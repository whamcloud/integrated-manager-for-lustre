// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    data::SessionToRpcs,
    local_actions::{handle_local_action, SharedLocalActionsInFlight},
    remote_action, Sessions, Shared,
};
use emf_postgres::sqlx::PgPool;
use emf_rabbit::Connection;
use emf_wire_types::ActionType;
use futures::TryFutureExt;
use std::sync::Arc;
use warp::{self, Filter};

pub fn sender(
    queue_name: impl Into<String>,
    sessions: Shared<Sessions>,
    session_to_rpcs: Shared<SessionToRpcs>,
    local_actions: SharedLocalActionsInFlight,
    client_filter: impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone + Send,
    db_pool: PgPool,
) -> impl Filter<Extract = (Result<serde_json::Value, String>,), Error = warp::Rejection> + Clone {
    let queue_name = queue_name.into();

    let sessions_filter = warp::any().map(move || Arc::clone(&sessions));
    let session_to_rpcs_filter = warp::any().map(move || Arc::clone(&session_to_rpcs));
    let local_actions_filter = warp::any().map(move || Arc::clone(&local_actions));
    let queue_name_filter = warp::any().map(move || queue_name.clone());
    let db_pool_filter = warp::any().map(move || db_pool.clone());

    let deps = sessions_filter
        .and(session_to_rpcs_filter)
        .and(local_actions_filter)
        .and(client_filter)
        .and(queue_name_filter)
        .and(db_pool_filter);

    warp::post().and(deps).and(warp::body::json()).and_then(
        move |shared_sessions: Shared<Sessions>,
              shared_session_to_rpcs: Shared<SessionToRpcs>,
              local_actions: SharedLocalActionsInFlight,
              conn: Connection,
              queue_name: String,
              db_pool: PgPool,
              action_type: ActionType| {
            async move {
                match action_type {
                    ActionType::Local(action) => {
                        tracing::debug!("Sending {:?}", action);

                        handle_local_action(action, local_actions, shared_sessions, db_pool).await
                    }
                    ActionType::Remote((fqdn, action)) => {
                        remote_action::run(
                            fqdn,
                            action,
                            shared_sessions,
                            shared_session_to_rpcs,
                            conn,
                            queue_name,
                        )
                        .await
                    }
                }
            }
            .map_err(warp::reject::custom)
        },
    )
}
