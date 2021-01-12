// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![type_length_limit = "1880654"]

use emf_action_runner::{
    data::SessionToRpcs, local_actions::SharedLocalActionsInFlight, receiver::handle_agent_data,
    sender::sender, Sessions, Shared,
};
use emf_manager_env::get_pool_limit;
use emf_postgres::get_db_pool;
use emf_rabbit::create_connection_filter;
use emf_service_queue::service_queue::{consume_service_queue, EmfServiceQueueError};
use emf_util::tokio_utils::get_tcp_or_unix_listener;
use futures::{lock::Mutex, FutureExt, TryFutureExt, TryStreamExt};
use std::{collections::HashMap, sync::Arc};
use warp::{self, Filter as _};

pub static AGENT_TX_RUST: &str = "agent_tx_rust";

// Default pool limit if not overridden by POOL_LIMIT
const POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let (exit, valve) = tokio_runtime_shutdown::shared_shutdown();

    let sessions: Shared<Sessions> = Arc::new(Mutex::new(HashMap::new()));
    let rpcs: Shared<SessionToRpcs> = Arc::new(Mutex::new(HashMap::new()));
    let local_actions: SharedLocalActionsInFlight = Arc::new(Mutex::new(HashMap::new()));

    let log = warp::log("emf_action_runner::sender");

    let pool = emf_rabbit::connect_to_rabbit(3);

    let db_pool = get_db_pool(get_pool_limit().unwrap_or(POOL_LIMIT)).await?;

    let routes = sender(
        AGENT_TX_RUST,
        Arc::clone(&sessions),
        Arc::clone(&rpcs),
        Arc::clone(&local_actions),
        create_connection_filter(pool.clone()),
        db_pool,
    )
    .map(|x| warp::reply::json(&x))
    .with(log);

    let mut listener = get_tcp_or_unix_listener("ACTION_RUNNER_PORT").await?;

    let incoming = listener.incoming();

    let conn = emf_rabbit::get_conn(pool.clone()).await?;
    let ch = emf_rabbit::create_channel(&conn).await?;

    let s = consume_service_queue(&ch, "rust_agent_action_runner_rx").await?;

    let mut s = exit.wrap(valve.wrap(s));

    drop(conn);

    tokio::spawn(
        async move {
            while let Some(m) = s.try_next().await? {
                tracing::debug!("Incoming message from agent: {:?}", m);

                let conn = emf_rabbit::get_conn(pool.clone()).await?;

                handle_agent_data(conn, m, Arc::clone(&sessions), Arc::clone(&rpcs))
                    .await
                    .unwrap_or_else(drop);
            }

            Ok(())
        }
        .map_err(|e: EmfServiceQueueError| {
            tracing::error!("{}", e);
        })
        .map(drop),
    );

    warp::serve(routes).run_incoming(incoming).await;

    Ok(())
}
