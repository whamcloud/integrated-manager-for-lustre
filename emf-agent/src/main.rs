// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_agent::{
    agent_error::Result,
    daemon_plugins, env,
    http_comms::{agent_client::AgentClient, crypto_client, session},
    poller, reader,
};
use env::{MANAGER_URL, PEM};
use futures::{
    future::{select, AbortHandle, Abortable},
    FutureExt, TryFutureExt,
};
use tokio::signal::unix::{signal, SignalKind};

#[tokio::main]
async fn main() -> Result<()> {
    emf_tracing::init();

    tracing::info!("Starting Rust agent_daemon");

    let message_endpoint = MANAGER_URL.join("/agent2/message/")?;

    let start_time = chrono::Utc::now().format("%Y-%m-%dT%T%.6f%:zZ").to_string();

    let identity = crypto_client::get_id(&PEM)?;
    let client = crypto_client::create_client(identity)?;

    let agent_client =
        AgentClient::new(start_time.clone(), message_endpoint.clone(), client.clone());

    let registry = daemon_plugins::plugin_registry();
    let registry_keys: Vec<emf_wire_types::PluginName> = registry.keys().cloned().collect();
    let sessions = session::Sessions::new(&registry_keys);

    let (reader, reader_reg) = AbortHandle::new_pair();
    tokio::spawn(Abortable::new(
        reader::create_reader(sessions.clone(), agent_client.clone(), registry)
            .map_err(|e| {
                tracing::error!("{}", e);
            })
            .map(drop),
        reader_reg,
    ));

    let (poller, poller_reg) = AbortHandle::new_pair();
    tokio::spawn(Abortable::new(
        poller::create_poller(agent_client, sessions.clone()),
        poller_reg,
    ));

    let mut sigterm = signal(SignalKind::terminate()).expect("Could not listen to SIGTERM");
    let mut sigint = signal(SignalKind::interrupt()).expect("Could not listen to SIGINT");
    select(sigterm.recv().boxed(), sigint.recv().boxed()).await;

    tracing::info!("Terminating on signal...");
    poller.abort();
    reader.abort();
    sessions.terminate_all_sessions().await?;

    Ok(())
}
