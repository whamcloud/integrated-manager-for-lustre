// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! #Network daemon-plugin
//!
//! This module is responsible for continually fetching the network interfaces and their respective stats.
//!
//!

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
    network_interfaces,
};
use futures::Future;
use iml_wire_types::{LNet, NetworkData, NetworkInterface};
use std::pin::Pin;

#[derive(Debug)]
pub struct Network;

pub fn create() -> impl DaemonPlugin {
    Network
}

async fn get_network_data<F1, F2>(
    get_interfaces: fn() -> F1,
    get_lnet_data: fn() -> F2,
) -> Result<Output, ImlAgentError>
where
    F1: Future<Output = Result<Vec<NetworkInterface>, ImlAgentError>>,
    F2: Future<Output = Result<LNet, ImlAgentError>>,
{
    let network_interfaces = get_interfaces().await?;
    let lnet_data = get_lnet_data().await?;

    let xs = NetworkData {
        network_interfaces,
        lnet_data,
    };

    Ok(serde_json::to_value(xs).map(Some)?)
}

impl DaemonPlugin for Network {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        self.update_session()
    }

    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let xs = get_network_data(
            network_interfaces::get_interfaces,
            network_interfaces::get_lnet_data,
        );
        Box::pin(xs)
    }
}
