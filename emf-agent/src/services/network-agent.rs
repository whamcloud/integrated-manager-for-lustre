// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_agent::{
    agent_error::EmfAgentError,
    env,
    network_interfaces::{get_interfaces, get_lnet_data},
    util::{create_filtered_writer, UnboundedSenderExt},
};
use emf_wire_types::NetworkData;
use std::time::Duration;
use tokio::time::interval;

async fn get_network_interfaces() -> Result<NetworkData, EmfAgentError> {
    let network_interfaces = get_interfaces().await?;
    let lnet_data = get_lnet_data().await?;

    Ok(NetworkData {
        network_interfaces,
        lnet_data,
    })
}

#[tokio::main]
async fn main() -> Result<(), EmfAgentError> {
    emf_tracing::init();

    let mut x = interval(Duration::from_secs(5));

    let port = env::get_port("NETWORK_AGENT_NETWORK_SERVICE_PORT");

    let writer = create_filtered_writer::<NetworkData>(port)?;

    loop {
        x.tick().await;

        let x = get_network_interfaces().await?;

        let _ = writer.send_msg(x);
    }
}
