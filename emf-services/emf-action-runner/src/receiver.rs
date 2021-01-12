// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    data::{create_data_message, remove_action_in_flight, SessionToRpcs},
    Sessions, Shared,
};
use emf_rabbit::{create_channel, send_message, Connection, EmfRabbitError};
use emf_wire_types::{ActionResult, Fqdn, Id, PluginMessage};
use futures::TryFutureExt;

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

async fn create_session(
    conn: Connection,
    sessions: Shared<Sessions>,
    rpcs: Shared<SessionToRpcs>,
    fqdn: Fqdn,
    session_id: Id,
) -> Result<(), ()> {
    let maybe_old_id = {
        sessions
            .lock()
            .await
            .insert(fqdn.clone(), session_id.clone())
    };

    if let Some(old_id) = maybe_old_id {
        if let Some(xs) = { rpcs.lock().await.remove(&old_id) } {
            for action_in_flight in xs.values() {
                let ch = create_channel(&conn)
                    .await
                    .expect("Could not create channel");

                let session_id = session_id.clone();
                let fqdn = fqdn.clone();
                let body = action_in_flight.action.clone();

                let msg = create_data_message(session_id, fqdn, body);

                tokio::spawn(
                    async move {
                        send_message(&ch, "", AGENT_TX_RUST, msg).await?;

                        emf_rabbit::close_channel(&ch).await?;

                        Ok(())
                    }
                    .unwrap_or_else(|e: EmfRabbitError| {
                        tracing::error!("Got an error resending rpcs {:?}", e)
                    }),
                );
            }

            drop(conn);

            rpcs.lock().await.insert(session_id.clone(), xs);
        };
    };

    tracing::info!("Created new session: {}/{}", fqdn, session_id);

    Ok(())
}

async fn handle_data(
    sessions: Shared<Sessions>,
    rpcs: Shared<SessionToRpcs>,
    fqdn: Fqdn,
    session_id: Id,
    body: serde_json::Value,
) {
    let mut sessions = sessions.lock().await;

    match sessions.get(&fqdn) {
        Some(held_session) if held_session == &session_id => {
            tracing::info!("good session {:?}/{:?}", fqdn, session_id);

            let result: Result<ActionResult, String> = serde_json::from_value(body).unwrap();

            let result = result.unwrap();

            let mut lock = rpcs.lock().await;

            match remove_action_in_flight(&session_id, &result.id, &mut lock) {
                Some(action_in_flight) => {
                    action_in_flight.complete(result.result).unwrap();
                }
                None => {
                    tracing::error!("Response received from UNKNOWN RPC of (id: {})", result.id);
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

pub async fn handle_agent_data(
    conn: Connection,
    m: PluginMessage,
    sessions: Shared<Sessions>,
    rpcs: Shared<SessionToRpcs>,
) -> Result<(), ()> {
    match m {
        PluginMessage::SessionCreate {
            fqdn, session_id, ..
        } => return create_session(conn, sessions, rpcs, fqdn, session_id).await,
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
        } => handle_data(sessions, rpcs, fqdn, session_id, body).await,
    };

    Ok(())
}
