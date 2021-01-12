// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    data::{
        await_session, create_data_message, has_action_in_flight, insert_action_in_flight,
        remove_action_in_flight, ActionInFlight, SessionToRpcs,
    },
    error::ActionRunnerError,
    Sessions, Shared,
};
use emf_rabbit::{send_message, Channel, Connection};
use emf_wire_types::{Action, ActionId, Fqdn, Id, ManagerMessage};
use futures::{channel::oneshot, TryFutureExt};
use serde_json::Value;
use std::time::Duration;

/// Attempts to cancel an `ActionInFlight`.
///
/// This fn will complete the `ActionInFlight` if it was successful.
/// It will also remove the `ActionInFlight` from the rpcs on success.
///
/// If unsuccessful, this fn will keep the `ActionInFlight` within the rpcs.
async fn cancel_running_action(
    ch: Channel,
    msg: ManagerMessage,
    queue_name: impl Into<String>,
    session_id: Id,
    action_id: ActionId,
    session_to_rpcs: Shared<SessionToRpcs>,
) -> Result<Result<serde_json::Value, String>, ActionRunnerError> {
    let has_action_in_flight = {
        let lock = session_to_rpcs.lock().await;
        has_action_in_flight(&session_id, &action_id, &lock)
    };

    if has_action_in_flight {
        send_message(&ch, "", queue_name, msg).await?;

        let mut lock = session_to_rpcs.lock().await;

        if let Some(action_in_flight) = remove_action_in_flight(&session_id, &action_id, &mut lock)
        {
            action_in_flight
                .complete(Ok(serde_json::Value::Null))
                .unwrap();
        }
    } else {
        tracing::info!(
            "Action {:?} not found, perhaps it was already cancelled.",
            action_id
        );
    }

    Ok(Ok(serde_json::Value::Null))
}

pub(crate) async fn run(
    fqdn: Fqdn,
    action: Action,
    shared_sessions: Shared<Sessions>,
    shared_session_to_rpcs: Shared<SessionToRpcs>,
    conn: Connection,
    queue_name: String,
) -> Result<Result<Value, String>, ActionRunnerError> {
    let session_id: Id =
        await_session(fqdn.clone(), shared_sessions, Duration::from_secs(30)).await?;

    tracing::debug!("Sending {:?} to {}", action, fqdn);

    let msg = create_data_message(session_id.clone(), fqdn, action.clone());

    let ch = emf_rabbit::create_channel(&conn).await?;

    drop(conn);

    let r = match action {
        Action::ActionCancel { id } => {
            cancel_running_action(
                ch.clone(),
                msg,
                queue_name,
                session_id,
                id,
                shared_session_to_rpcs,
            )
            .await
        }
        action => {
            let (tx, rx) = oneshot::channel();

            let action_id: ActionId = action.get_id().clone();
            let af = ActionInFlight::new(action, tx);

            {
                let mut lock = shared_session_to_rpcs.lock().await;

                insert_action_in_flight(session_id.clone(), action_id.clone(), af, &mut lock);
            }

            let x = send_message(&ch, "", queue_name, msg).err_into().await;

            if let Err(e) = x {
                tracing::error!("Message send failed {}", e);

                let mut lock = shared_session_to_rpcs.lock().await;

                remove_action_in_flight(&session_id, &action_id, &mut lock);

                return Err(e);
            }

            rx.await.map_err(|e| e.into())
        }
    };

    emf_rabbit::close_channel(&ch).await?;

    r
}
