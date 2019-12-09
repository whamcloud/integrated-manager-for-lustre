// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{lock::Mutex, prelude::*};
use iml_action_runner::{
    data::SessionToRpcs,
    local_actions::SharedLocalActionsInFlight,
    receiver::handle_agent_data,
    sender::{create_client_filter, sender},
    Sessions, Shared,
};
use iml_service_queue::service_queue::consume_service_queue;
use iml_util::tokio_utils::get_tcp_or_unix_listener;
use std::{collections::HashMap, sync::Arc};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::{self, Filter as _};

pub static AGENT_TX_RUST: &str = "agent_tx_rust";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let (exit, valve) = tokio_runtime_shutdown::shared_shutdown();

    let sessions: Shared<Sessions> = Arc::new(Mutex::new(HashMap::new()));
    let rpcs: Shared<SessionToRpcs> = Arc::new(Mutex::new(HashMap::new()));
    let local_actions: SharedLocalActionsInFlight = Arc::new(Mutex::new(HashMap::new()));

    let log = warp::log("iml_action_runner::sender");

    let (fut, client_filter) = create_client_filter().await?;

    tokio::spawn(fut);

    let routes = sender(
        AGENT_TX_RUST,
        Arc::clone(&sessions),
        Arc::clone(&rpcs),
        Arc::clone(&local_actions),
        client_filter,
    )
    .map(|x| warp::reply::json(&x))
    .with(log);

    let listener = get_tcp_or_unix_listener("ACTION_RUNNER_PORT").await?;

    tokio::spawn(warp::serve(routes).serve_incoming(listener));

    let client = iml_rabbit::connect_to_rabbit().await?;

    let mut s = exit.wrap(valve.wrap(consume_service_queue(
        client.clone(),
        "rust_agent_action_runner_rx",
    )));

    while let Some(m) = s.try_next().await? {
        tracing::debug!("Incoming message from agent: {:?}", m);

        handle_agent_data(client.clone(), m, Arc::clone(&sessions), Arc::clone(&rpcs))
            .await
            .unwrap_or_else(drop);
    }

    Ok(())
}
