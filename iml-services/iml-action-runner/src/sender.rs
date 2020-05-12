// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    data::{
        await_session, create_data_message, has_action_in_flight, insert_action_in_flight,
        remove_action_in_flight, ActionInFlight, SessionToRpcs,
    },
    error::ActionRunnerError,
    local_actions::{handle_local_action, SharedLocalActionsInFlight},
    ActionType, Sessions, Shared,
};
use futures::{channel::oneshot, TryFutureExt};
use iml_rabbit::{send_message, Connection};
use iml_wire_types::{Action, ActionId, Id, ManagerMessage};
use std::{sync::Arc, time::Duration};
use warp::{self, Filter};

/// Attempts to cancel an `ActionInFlight`.
///
/// This fn will complete the `ActionInFlight` if it was successful.
/// It will also remove the `ActionInFlight` from the rpcs on success.
///
/// If unsuccessful, this fn will keep the `ActionInFlight` within the rpcs.
async fn cancel_running_action(
    client: Connection,
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
        send_message(client.clone(), "", queue_name, msg).await?;

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

pub fn sender(
    queue_name: impl Into<String>,
    sessions: Shared<Sessions>,
    session_to_rpcs: Shared<SessionToRpcs>,
    local_actions: SharedLocalActionsInFlight,
    client_filter: impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone + Send,
) -> impl Filter<Extract = (Result<serde_json::Value, String>,), Error = warp::Rejection> + Clone {
    let queue_name = queue_name.into();

    let sessions_filter = warp::any().map(move || Arc::clone(&sessions));
    let session_to_rpcs_filter = warp::any().map(move || Arc::clone(&session_to_rpcs));
    let local_actions_filter = warp::any().map(move || Arc::clone(&local_actions));
    let queue_name_filter = warp::any().map(move || queue_name.clone());

    let deps = sessions_filter
        .and(session_to_rpcs_filter)
        .and(local_actions_filter)
        .and(client_filter)
        .and(queue_name_filter);

    warp::post().and(deps).and(warp::body::json()).and_then(
        move |shared_sessions: Shared<Sessions>,
              shared_session_to_rpcs: Shared<SessionToRpcs>,
              local_actions: SharedLocalActionsInFlight,
              client: Connection,
              queue_name: String,
              action_type: ActionType| {
            async move {
                match action_type {
                    ActionType::Local(action) => {
                        tracing::debug!("Sending {:?}", action);

                        handle_local_action(action, local_actions, shared_sessions).await
                    }
                    ActionType::Remote((fqdn, action)) => {
                        let session_id: Id =
                            await_session(fqdn.clone(), shared_sessions, Duration::from_secs(30))
                                .await?;

                        tracing::debug!("Sending {:?} to {}", action, fqdn);

                        let msg = create_data_message(session_id.clone(), fqdn, action.clone());

                        match action {
                            Action::ActionCancel { id } => {
                                cancel_running_action(
                                    client.clone(),
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

                                    insert_action_in_flight(
                                        session_id.clone(),
                                        action_id.clone(),
                                        af,
                                        &mut lock,
                                    );
                                }

                                let x = send_message(client.clone(), "", queue_name, msg)
                                    .err_into()
                                    .await;

                                if let Err(e) = x {
                                    tracing::error!("Message send failed {}", e);

                                    let mut lock = shared_session_to_rpcs.lock().await;

                                    remove_action_in_flight(&session_id, &action_id, &mut lock);

                                    return Err(e);
                                }

                                rx.await.map_err(|e| e.into())
                            }
                        }
                    }
                }
            }
            .map_err(warp::reject::custom)
        },
    )
}
