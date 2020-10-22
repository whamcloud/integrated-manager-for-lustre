// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_agent::{
    action_plugins::create_registry,
    action_plugins::postoffice::{unlock_file, UnlockOp},
    agent_error::{EmfAgentError, RequiredError},
    env,
    util::{wait_for_termination, FQDN},
};
use emf_request_retry::{policy::exponential_backoff_policy_builder, retry_future};
use emf_wire_types::{Action, ActionId, ActionResult, ToJsonValue};
use futures::{
    future::{AbortHandle, Abortable},
    StreamExt,
};
use http::header;
use once_cell::sync::Lazy;
use reqwest::Client;
use std::{collections::HashMap, time::Duration};
use tokio::{
    sync::mpsc::{unbounded_channel, UnboundedSender},
    time::interval,
};
use tokio_stream::wrappers::UnboundedReceiverStream;
use uuid::Uuid;

enum StateMsg {
    Insert(ActionId, AbortHandle),
    Remove(ActionId),
    Drain,
}

static STATE_MACHINE_SERVICE: Lazy<String> = Lazy::new(|| {
    let port = env::get_port("ACTION_AGENT_STATE_MACHINE_SERVICE_PORT");

    format!("http://127.0.0.1:{}", port)
});

#[tokio::main]
async fn main() -> Result<(), EmfAgentError> {
    emf_tracing::init();

    // ensure postoffice lock file is removed on restart
    let _ = unlock_file(UnlockOp::Drop).await;

    let instance_id = Uuid::new_v4().to_string();

    let mut headers = header::HeaderMap::new();
    headers.insert("x-client-fqdn", header::HeaderValue::from_static(&FQDN));
    headers.insert(
        "x-instance-id",
        header::HeaderValue::from_str(&instance_id)?,
    );

    let client = Client::builder()
        .connect_timeout(Duration::from_secs(5))
        .http2_prior_knowledge()
        .default_headers(headers)
        .build()?;

    let state_tx = state_handler();

    let writer = result_writer(client.clone());

    let fut = action_handler(client, writer, state_tx.clone());

    tokio::spawn(async move {
        wait_for_termination().await;

        let _ = state_tx.clone().send(StateMsg::Drain);
    });

    fut.await?;

    Ok(())
}

/// This fn provides lockless management of in-flight rpc calls.
fn state_handler() -> UnboundedSender<StateMsg> {
    let (tx, rx) = unbounded_channel();
    let mut rx = UnboundedReceiverStream::new(rx);

    let mut state = HashMap::new();

    tokio::spawn(async move {
        while let Some(x) = rx.next().await {
            match x {
                StateMsg::Insert(id, hdl) => {
                    state.insert(id.clone(), hdl);
                }
                StateMsg::Remove(id) => {
                    let x = state.remove(&id);

                    if let Some(x) = x {
                        x.abort();
                    }
                }
                StateMsg::Drain => {
                    for (_, x) in state.drain() {
                        x.abort();
                    }
                }
            };
        }
    });

    tx
}

async fn action_handler(
    client: Client,
    writer: UnboundedSender<ActionResult>,
    state_tx: UnboundedSender<StateMsg>,
) -> Result<(), EmfAgentError> {
    let registry = create_registry();

    let mut x = interval(Duration::from_secs(5));

    loop {
        x.tick().await;

        let actions = fetch_actions(client.clone()).await?;

        for action in actions {
            let state_tx = state_tx.clone();
            let writer = writer.clone();

            match action {
                Action::ActionStart { action, args, id } => {
                    let action_plugin_fn = match registry.get(&action) {
                        Some(x) => x,
                        None => {
                            let err = RequiredError(format!(
                                "Could not find action {} in registry",
                                action
                            ));

                            let result = ActionResult {
                                id,
                                result: Err(format!("{:?}", err)),
                            };

                            let _ = writer.send(result);

                            continue;
                        }
                    };

                    let (abort_handle, abort_registration) = AbortHandle::new_pair();

                    let _ = state_tx.send(StateMsg::Insert(id.clone(), abort_handle));

                    let fut = action_plugin_fn(args);
                    let fut = Abortable::new(fut, abort_registration);

                    tokio::spawn(async move {
                        let r = fut.await;

                        let _ = state_tx.send(StateMsg::Remove(id.clone()));

                        let r = match r {
                            Ok(result) => ActionResult { id, result },
                            Err(_) => ActionResult {
                                id,
                                result: ().to_json_value(),
                            },
                        };

                        let _ = writer.send(r);
                    });
                }
                Action::ActionCancel { id } => {
                    let _ = state_tx.send(StateMsg::Remove(id.clone()));

                    let r = ActionResult {
                        id,
                        result: ().to_json_value(),
                    };

                    let _ = writer.send(r);
                }
            };
        }
    }
}

async fn fetch_actions(client: Client) -> Result<Vec<Action>, EmfAgentError> {
    let policy = exponential_backoff_policy_builder().build();

    let x = retry_future(|_| client.get(&*STATE_MACHINE_SERVICE).send(), policy)
        .await
        .and_then(|resp| resp.error_for_status())?
        .json()
        .await?;

    Ok(x)
}

/// Responsible for sending `ActionResult`s back to the state-machine.
/// Any failures to send will be retried.
fn result_writer(client: Client) -> UnboundedSender<ActionResult> {
    let (tx, rx) = unbounded_channel();
    let mut rx = UnboundedReceiverStream::new(rx);

    tokio::spawn(async move {
        while let Some(x) = rx.next().await {
            let policy = exponential_backoff_policy_builder().build();

            let r = retry_future(
                |_| client.post(&*STATE_MACHINE_SERVICE).json(&x).send(),
                policy,
            )
            .await
            .and_then(|resp| resp.error_for_status());

            if let Err(e) = r {
                tracing::error!("Could not send result {:?}. Error {:?}", x, e);
            }
        }
    });

    tx
}
