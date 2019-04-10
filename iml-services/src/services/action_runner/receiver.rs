// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::services::action_runner::data::{
    create_data_message, remove_action_in_flight, SessionToRpcs, Sessions, Shared,
};
use futures::Future as _;
use iml_manager_messaging::send_agent_message;
use iml_rabbit::TcpClient;
use iml_wire_types::{ActionResult, Fqdn, PluginMessage};

fn terminate_session(fqdn: &Fqdn, sessions: &mut Sessions, session_to_rpcs: &mut SessionToRpcs) {
    if let Some(old_id) = sessions.remove(fqdn) {
        if let Some(mut xs) = session_to_rpcs.remove(&old_id) {
            for (_, action_in_flight) in xs.drain() {
                let msg = Err(format!(
                    "Communications error, Node: {}, Reason: session terminated",
                    fqdn
                ));

                action_in_flight.complete(msg).unwrap();
            }
        }
    }
}

pub fn hande_agent_data(
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

                        tokio::spawn(
                            send_agent_message(
                                client.clone(),
                                "",
                                iml_manager_messaging::AGENT_TX_RUST,
                                msg,
                            )
                            .map(|_| ())
                            .map_err(|e| log::error!("Got an error resending rpcs {:?}", e)),
                        );
                    }
                    rpcs.lock().insert(session_id.clone(), xs);
                };
            };
        }
        PluginMessage::SessionTerminate {
            fqdn, session_id, ..
        } => match sessions.lock().get(&fqdn) {
            Some(held_session) if held_session == &session_id => {
                terminate_session(&fqdn, &mut sessions.lock(), &mut rpcs.lock());
            }
            Some(unknown_session) => {
                log::info!(
                    "unknown session. Wanted: {}/{:?}, Got: {}/{:?}",
                    fqdn,
                    session_id,
                    fqdn,
                    unknown_session
                );
            }
            None => {
                log::info!("unknown session {:?}/{:?}", fqdn, session_id);
            }
        },
        PluginMessage::Data {
            fqdn,
            session_id,
            body,
            ..
        } => match sessions.lock().get(&fqdn) {
            Some(held_session) if held_session == &session_id => {
                log::info!("good session {:?}/{:?}", fqdn, session_id);

                let result: Result<ActionResult, String> = serde_json::from_value(body).unwrap();

                let result = result.unwrap();

                match remove_action_in_flight(&session_id, &result.id, &mut rpcs.lock()) {
                    Some(action_in_flight) => {
                        action_in_flight.complete(result.result).unwrap();
                    }
                    None => {
                        log::error!("Response received from UNKNOWN RPC of (id: {})", result.id);
                    }
                };
            }
            Some(held_session) => {
                log::info!(
                    "cancelling session {:?}/{:?} (replaced by {:?})",
                    fqdn,
                    held_session,
                    session_id
                );

                terminate_session(&fqdn, &mut sessions.lock(), &mut rpcs.lock());
            }
            None => {
                log::info!("unknown session {:?}/{:?}", fqdn, session_id);
            }
        },
    };
}
