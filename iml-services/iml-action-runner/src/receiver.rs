// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    data::{create_data_message, remove_action_in_flight, SessionToRpcs},
    Sessions, Shared,
};
use iml_rabbit::{send_message, Client};
use iml_wire_types::{ActionResult, Fqdn, PluginMessage};

pub static AGENT_TX_RUST: &str = "agent_tx_rust";

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

pub async fn handle_agent_data(
    client: Client,
    m: PluginMessage,
    sessions: Shared<Sessions>,
    rpcs: Shared<SessionToRpcs>,
) -> Result<(), ()> {
    match m {
        PluginMessage::SessionCreate {
            fqdn, session_id, ..
        } => {
            let maybe_old_id = {
                sessions
                    .lock()
                    .await
                    .insert(fqdn.clone(), session_id.clone())
            };

            if let Some(old_id) = maybe_old_id {
                if let Some(xs) = { rpcs.lock().await.remove(&old_id) } {
                    for action_in_flight in xs.values() {
                        let session_id = session_id.clone();
                        let fqdn = fqdn.clone();
                        let body = action_in_flight.action.clone();

                        let msg = create_data_message(session_id, fqdn, body);

                        let fut = send_message(client.clone(), "", AGENT_TX_RUST, msg);

                        tokio::spawn(async move {
                            fut.await.unwrap_or_else(|e| {
                                tracing::error!("Got an error resending rpcs {:?}", e)
                            });
                        });
                    }

                    rpcs.lock().await.insert(session_id.clone(), xs);
                };
            };

            tracing::info!("Created new session: {}/{}", fqdn, session_id);
        }
        PluginMessage::SessionTerminate {
            fqdn, session_id, ..
        } => {
            let mut sessions = sessions.lock().await;

            match sessions.get(&fqdn) {
                Some(held_session) if held_session == &session_id => {
                    let mut lock = rpcs.lock().await;
                    terminate_session(&fqdn, &mut sessions, &mut lock);

                    tracing::info!("Terminated session: {}/{}", fqdn, session_id);
                }
                Some(unknown_session) => {
                    tracing::info!(
                        "unknown session. Wanted: {}/{:?}, Got: {}/{:?}",
                        fqdn,
                        session_id,
                        fqdn,
                        unknown_session
                    );
                }
                None => {
                    tracing::info!("unknown session {}/{}", fqdn, session_id);
                }
            }
        }
        PluginMessage::Data {
            fqdn,
            session_id,
            body,
            ..
        } => {
            let mut sessions = sessions.lock().await;

            match sessions.get(&fqdn) {
                Some(held_session) if held_session == &session_id => {
                    tracing::info!("good session {:?}/{:?}", fqdn, session_id);

                    let result: Result<ActionResult, String> =
                        serde_json::from_value(body).unwrap();

                    let result = result.unwrap();

                    let mut lock = rpcs.lock().await;

                    match remove_action_in_flight(&session_id, &result.id, &mut lock) {
                        Some(action_in_flight) => {
                            action_in_flight.complete(result.result).unwrap();
                        }
                        None => {
                            tracing::error!(
                                "Response received from UNKNOWN RPC of (id: {})",
                                result.id
                            );
                        }
                    };
                }
                Some(held_session) => {
                    tracing::info!(
                        "cancelling session {}/{} (replaced by {:?})",
                        fqdn,
                        held_session,
                        session_id
                    );

                    let mut lock = rpcs.lock().await;

                    terminate_session(&fqdn, &mut sessions, &mut lock);
                }
                None => {
                    tracing::info!("unknown session {:?}/{:?}", fqdn, session_id);
                }
            }
        }
    };

    Ok(())
}
