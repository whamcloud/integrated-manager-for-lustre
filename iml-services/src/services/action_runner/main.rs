// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::lazy;
use iml_manager_messaging::{send_agent_message, send_direct_reply, RoutingKey};
use iml_rabbit::TcpClient;
use iml_services::{
    service_queue::consume_service_queue, services::action_runner::consume_from_manager,
};
use iml_wire_types::{
    Action, ActionId, ActionResult, Fqdn, Id, ManagerMessage, PluginMessage, PluginName,
};
use parking_lot::Mutex;
use std::{collections::HashMap, sync::Arc};
use tokio::prelude::*;

type Shared<T> = Arc<Mutex<T>>;
type Sessions = HashMap<Fqdn, Id>;
type Rpcs<'a> = HashMap<Id, HashMap<&'a ActionId, ActionInFlight<'a>>>;

struct ActionInFlight<'a> {
    routing_key: RoutingKey<'a>,
    action: Action,
}

fn main() {
    env_logger::init();

    let (exit, valve) = tokio_runtime_shutdown::shared_shutdown();

    let sessions: Shared<Sessions> = Arc::new(Mutex::new(HashMap::new()));
    let rpcs: Shared<Rpcs> = Arc::new(Mutex::new(HashMap::new()));

    // fn abort_session(fqdn: Fqdn) {}

    // fn replay_rpcs<'a>(client: TcpClient, rpcs: &'a mut Rpcs<'a>, old_id: &Id, new_id: &'a Id) {
    //     if let Some(xs) = rpcs.remove(old_id) {
    //         for action_in_flight in xs.values() {
    //             // tokio::spawn(send_agent_message(client, msg));
    //         }
    //         rpcs.insert(new_id, xs);
    //     };
    // }

    fn msg_factory<'a>(
        session_id: &'a Id,
        fqdn: &'a Fqdn,
    ) -> impl Fn(serde_json::Value) -> ManagerMessage + 'a {
        move |body| ManagerMessage::Data {
            session_id: session_id.clone(),
            fqdn: fqdn.clone(),
            plugin: PluginName("action_runner".to_string()),
            body,
        }
    }

    fn hande_agent_data(
        client: TcpClient,
        m: PluginMessage,
        sessions: &Shared<Sessions>,
        rpcs: Shared<Rpcs>,
    ) {
        match m {
            PluginMessage::SessionCreate {
                fqdn, session_id, ..
            } => {
                let mut sessions = sessions.lock();

                if let Some(old_id) = sessions.insert(fqdn.clone(), session_id.clone()) {
                    if let Some(xs) = rpcs.lock().remove(&old_id) {
                        let create_msg = msg_factory(&session_id, &fqdn);

                        for action_in_flight in xs.values() {
                            let msg =
                                create_msg(serde_json::to_value(&action_in_flight.action).unwrap());

                            send_agent_message(client.clone(), msg);
                        }
                        rpcs.lock().insert(session_id.clone(), xs);
                    };
                };
            }
            PluginMessage::SessionTerminate {
                fqdn, session_id, ..
            } => {
                if let Some(old_id) = sessions.lock().remove(&fqdn) {
                    if let Some(mut xs) = rpcs.lock().remove(&old_id) {
                        for (_, action_in_flight) in xs.drain() {
                            let msg: Result<(), String> = Err(format!(
                                "Communications error, Node: {}, Reason: session terminated",
                                fqdn
                            ));

                            send_direct_reply(client.clone(), action_in_flight.routing_key, msg);
                        }
                    }
                }
            }
            PluginMessage::Data {
                fqdn,
                session_id,
                body,
                ..
            } => match sessions.lock().get(&fqdn) {
                Some(held_session) if held_session == &session_id => {
                    log::info!("good session {:?}/{:?}", fqdn, session_id);

                    match rpcs.lock().get_mut(&session_id) {
                        Some(rs) => {
                            let result: Result<ActionResult, String> =
                                serde_json::from_value(body).unwrap();

                            let result = result.unwrap();

                            match rs.remove(&result.id) {
                                Some(action_in_flight) => {
                                    send_direct_reply(
                                        client.clone(),
                                        action_in_flight.routing_key,
                                        result.result,
                                    );
                                }
                                None => {
                                    log::error!(
                                        "Response received from UNKNOWN RPC of (id: {})",
                                        result.id
                                    );
                                }
                            }
                        }
                        None => {}
                    }
                }
                Some(held_session) => {
                    log::info!(
                        "cancelling session {:?}/{:?} (replaced by {:?})",
                        fqdn,
                        held_session,
                        session_id
                    );

                    if let Some(old_id) = sessions.lock().remove(&fqdn) {
                        if let Some(mut xs) = rpcs.lock().remove(&old_id) {
                            for (_, action_in_flight) in xs.drain() {
                                let msg: Result<(), String> = Err(format!(
                                    "Communications error, Node: {}, Reason: session terminated",
                                    fqdn
                                ));

                                send_direct_reply(
                                    client.clone(),
                                    action_in_flight.routing_key,
                                    msg,
                                );
                            }
                        }
                    }
                }
                None => {
                    log::info!("unknown session {:?}/{:?}", fqdn, session_id);
                }
            },
        };
    }

    tokio::run(lazy(move || {
        let fut = valve
            .wrap(consume_from_manager::start())
            .for_each(|_| Ok(()))
            .map_err(exit.trigger_fn())
            .map_err(|e| log::error!("An error occured: {:?}", e));

        tokio::spawn(fut);

        iml_rabbit::connect_to_rabbit()
            .and_then(move |client| {
                valve
                    .wrap(consume_service_queue(
                        client.clone(),
                        "agent_action_runner_rx",
                    ))
                    .for_each(move |m: PluginMessage| {
                        log::info!("Got some actiony data: {:?}", m);

                        hande_agent_data(client.clone(), m, &sessions, Arc::clone(&rpcs));

                        Ok(())
                    })
            })
            .map_err(exit.trigger_fn())
            .map_err(|e| log::error!("An error occured: {:?}", e))
    }));
}
