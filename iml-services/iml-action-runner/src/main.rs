// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{lock::Mutex, prelude::*};
use iml_action_runner::{
    data::{SessionToRpcs, Sessions, Shared},
    receiver::handle_agent_data,
    sender::{create_client_filter, sender},
};
use iml_service_queue::service_queue::consume_service_queue;
use std::{
    collections::HashMap,
    convert::TryFrom,
    os::unix::{io::FromRawFd, net::UnixListener as NetUnixListener},
    sync::Arc,
};
use tokio::net::UnixListener;
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

    let log = warp::log("iml_action_runner::sender");

    let (fut, client_filter) = create_client_filter().await?;

    tokio::spawn(fut);

    let routes = sender(
        AGENT_TX_RUST,
        Arc::clone(&sessions),
        Arc::clone(&rpcs),
        client_filter,
    )
    .map(|x| warp::reply::json(&x))
    .with(log);

    let addr = unsafe { NetUnixListener::from_raw_fd(3) };

    let listener = UnixListener::try_from(addr)?
        .incoming()
        .inspect_ok(|_| tracing::debug!("Client connected"));

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
