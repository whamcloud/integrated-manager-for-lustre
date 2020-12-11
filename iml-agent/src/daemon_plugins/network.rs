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
    network_interfaces::{get_interfaces, get_lnet_data},
};
use futures::Future;
use iml_wire_types::NetworkData;
use std::pin::Pin;

#[derive(Clone, Debug)]
pub struct Network;

pub fn create() -> impl DaemonPlugin {
    Network
}

async fn get_network_interfaces() -> Result<Output, ImlAgentError> {
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
        Box::pin(get_network_interfaces())
    }
}
