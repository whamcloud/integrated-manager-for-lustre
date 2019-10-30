// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use env::{MANAGER_URL, PFX};
use futures::{FutureExt, TryFutureExt};
use iml_agent::{
    agent_error::Result,
    daemon_plugins, env,
    http_comms::{agent_client::AgentClient, crypto_client, session},
    poller, reader,
};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<()> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    tracing::info!("Starting Rust agent_daemon");

    let message_endpoint = MANAGER_URL.join("/agent2/message/")?;

    let start_time = chrono::Utc::now().format("%Y-%m-%dT%T%.6f%:zZ").to_string();

    let identity = crypto_client::get_id(&PFX)?;
    let client = crypto_client::create_client(identity)?;

    let agent_client =
        AgentClient::new(start_time.clone(), message_endpoint.clone(), client.clone());

    let registry = daemon_plugins::plugin_registry();
    let registry_keys: Vec<iml_wire_types::PluginName> = registry.keys().cloned().collect();
    let sessions = session::Sessions::new(&registry_keys);

    tokio::spawn(
        reader::create_reader(sessions.clone(), agent_client.clone(), registry)
            .map_err(|e| {
                tracing::error!("{}", e);
            })
            .map(drop),
    );

    poller::create_poller(agent_client, sessions).await?;

    Ok(())
}
