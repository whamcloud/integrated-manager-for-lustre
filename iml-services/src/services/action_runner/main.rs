// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future::Future, lazy, stream::Stream};
use iml_manager_messaging::send_agent_message;
use iml_rabbit::TcpClient;
use iml_services::{
    service_queue::consume_service_queue,
    services::action_runner::{
        data::{SessionToRpcs, Sessions, Shared},
        sender::{create_client_filter, sender},
    },
};
use iml_wire_types::{ActionResult, Fqdn, Id, ManagerMessage, PluginMessage, PluginName};
use parking_lot::Mutex;
use std::{
    collections::HashMap,
    os::unix::{io::FromRawFd, net::UnixListener as NetUnixListener},
    sync::Arc,
};
use tokio::{net::UnixListener, reactor::Handle};
use warp::{self, Filter as _};

fn create_data_message(
    session_id: Id,
    fqdn: Fqdn,
    body: impl Into<serde_json::Value>,
) -> ManagerMessage {
    ManagerMessage::Data {
        session_id,
        fqdn,
        plugin: PluginName("action_runner".to_string()),
        body: body.into(),
    }
}

fn hande_agent_data(
    client: TcpClient,
    m: PluginMessage,
    sessions: &Shared<Sessions>,
    rpcs: Shared<SessionToRpcs>,
) {
    match m {
        PluginMessage::SessionCreate {
            fqdn, session_id, ..
        } => {
            let mut sessions = sessions.lock();

            if let Some(old_id) = sessions.insert(fqdn.clone(), session_id.clone()) {
                if let Some(xs) = rpcs.lock().remove(&old_id) {
                    for action_in_flight in xs.values() {
                        let session_id = session_id.clone();
                        let fqdn = fqdn.clone();
                        let body = action_in_flight.action.clone();

                        let msg = create_data_message(session_id, fqdn, body);

                        send_agent_message(client.clone(), "", msg);
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
                        let msg = Err(format!(
                            "Communications error, Node: {}, Reason: session terminated",
                            fqdn
                        ));

                        action_in_flight.complete(msg);
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
                                action_in_flight.complete(result.result);
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
                            let msg = Err(format!(
                                "Communications error, Node: {}, Reason: session terminated",
                                fqdn
                            ));

                            action_in_flight.complete(msg);
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

fn main() {
    env_logger::init();

    let (exit, valve) = tokio_runtime_shutdown::shared_shutdown();

    let sessions: Shared<Sessions> = Arc::new(Mutex::new(HashMap::new()));
    let rpcs: Shared<SessionToRpcs> = Arc::new(Mutex::new(HashMap::new()));

    tokio::run(lazy(move || {
        let addr = unsafe { NetUnixListener::from_raw_fd(3) };

        let listener = UnixListener::from_std(addr, &Handle::default())
            .expect("Unable to bind Unix Domain Socket fd");

        let log = warp::log("iml_action_runner::sender");

        let (fut, client_filter) = create_client_filter();

        tokio::spawn(fut);

        let routes = sender("", Arc::clone(&sessions), Arc::clone(&rpcs), client_filter)
            .map(|x| warp::reply::json(&x))
            .with(log);

        tokio::spawn(warp::serve(routes).serve_incoming(valve.wrap(listener.incoming())));

        iml_rabbit::connect_to_rabbit()
            .and_then(move |client| {
                exit.wrap(valve.wrap(consume_service_queue(
                    client.clone(),
                    "rust_agent_action_runner_rx",
                )))
                .for_each(move |m: PluginMessage| {
                    log::debug!("Incoming message from agent: {:?}", m);

                    hande_agent_data(client.clone(), m, &sessions, Arc::clone(&rpcs));

                    Ok(())
                })
            })
            .map_err(|e| log::error!("An error occured (agent side): {:?}", e))
    }));
}
