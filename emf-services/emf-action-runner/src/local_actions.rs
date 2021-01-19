// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    data::{await_next_session, get_session},
    db,
    error::{self, ActionRunnerError},
    Sender, Sessions, Shared,
};
use emf_postgres::sqlx;
use emf_wire_types::{Action, ActionId, ToJsonValue};
use futures::{channel::oneshot, future::BoxFuture, Future, FutureExt, TryFutureExt};
use serde_json::value::Value;
use std::{collections::HashMap, fmt::Display, ops::Deref, sync::Arc};

pub type LocalActionsInFlight = HashMap<ActionId, Sender>;
pub type SharedLocalActionsInFlight = Shared<LocalActionsInFlight>;

/// Adds an action id to the in-flight list.
/// A tx handle is stored internally, and the rx side is returned.
///
/// The rx will resolve once the plugin has completed or is cancelled.
async fn add_in_flight(
    in_flight: SharedLocalActionsInFlight,
    id: ActionId,
) -> oneshot::Receiver<Result<Value, String>> {
    let (tx, rx) = oneshot::channel();

    let mut in_flight = in_flight.lock().await;

    in_flight.insert(id.clone(), tx);

    rx
}

/// Removes an action id from the in-flight list.
///
/// Returns the tx handle which can then be used to cancel the action if needed.
async fn remove_in_flight(
    in_flight: SharedLocalActionsInFlight,
    id: &ActionId,
) -> Option<oneshot::Sender<Result<Value, String>>> {
    let mut in_flight = in_flight.lock().await;

    in_flight.remove(id).or_else(|| {
        tracing::info!(
            "Local action {:?} not found, perhaps it was already cancelled.",
            id
        );

        None
    })
}

/// Spawn the plugin within a new task.
///
/// When the plugin completes or is cancelled, it will notify the rx
/// handle associated with the action id.
pub fn spawn_plugin(
    fut: impl Future<Output = Result<Value, String>> + Send + 'static,
    in_flight: SharedLocalActionsInFlight,
    id: ActionId,
) {
    tokio::spawn(fut.then(move |result| async move {
        let _ = remove_in_flight(in_flight, &id)
            .await
            .map(|tx| tx.send(result));
    }));
}

/// Wraps a `FnOnce` so it will be called with a deserialized value and return a serialized value.
///
/// This is subetly different from a usual action plugin in that it's meant to be used with closures.
fn wrap_plugin<T, R, E: Display, Fut>(
    v: Value,
    f: impl FnOnce(T) -> Fut + Send + 'static,
) -> BoxFuture<'static, Result<Value, String>>
where
    T: serde::de::DeserializeOwned + Send,
    R: serde::Serialize + Send,
    Fut: Future<Output = Result<R, E>> + Send,
{
    Box::pin(async {
        let x = serde_json::from_value(v).map_err(|e| format!("{}", e))?;

        let x = f(x).await.map_err(|e| format!("{}", e))?;

        x.to_json_value()
    })
}

async fn run_plugin(
    id: ActionId,
    in_flight: SharedLocalActionsInFlight,
    fut: impl Future<Output = Result<Value, String>> + Send + 'static,
) -> Result<Result<serde_json::value::Value, String>, ActionRunnerError> {
    let rx = add_in_flight(Arc::clone(&in_flight), id.clone()).await;

    spawn_plugin(fut, in_flight, id);

    rx.err_into().await
}

/// Try to locate and start or cancel a local action.
pub async fn handle_local_action(
    action: Action,
    in_flight: SharedLocalActionsInFlight,
    sessions: Shared<Sessions>,
    db_pool: sqlx::PgPool,
) -> Result<Result<serde_json::value::Value, String>, ActionRunnerError> {
    match action {
        Action::ActionCancel { id } => {
            let _ = remove_in_flight(in_flight, &id)
                .await
                .map(|tx| tx.send(Ok(serde_json::Value::Null)));

            Ok(Ok(serde_json::Value::Null))
        }
        Action::ActionStart { id, action, args } => {
            let plugin = match action.deref() {
                "get_session" => wrap_plugin(args, move |fqdn| get_session(fqdn, sessions)),
                "await_next_session" => {
                    wrap_plugin(args, move |(fqdn, last_session, wait_secs)| {
                        await_next_session(fqdn, last_session, wait_secs, sessions)
                    })
                }
                "get_fqdn_by_id" => {
                    wrap_plugin(args, move |id: i32| db::get_host_fqdn_by_id(id, db_pool))
                }
                _ => {
                    return Err(ActionRunnerError::RequiredError(error::RequiredError(
                        format!("Could not find action {} in local registry", action),
                    )))
                }
            };

            run_plugin(id, in_flight, plugin).await
        }
    }
}
