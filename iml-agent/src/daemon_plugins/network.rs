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
use iml_wire_types::NetworkInterface;
use std::pin::Pin;

#[derive(Debug)]
pub struct Network;

pub fn create() -> impl DaemonPlugin {
    Network
}

async fn get_network_interfaces<F1>(get_interfaces: fn() -> F1) -> Result<Output, ImlAgentError>
where
    F1: Future<Output = Result<Vec<NetworkInterface>, ImlAgentError>>,
{
    let xs = get_interfaces().await?;
    let xs = serde_json::to_value(xs).map(Some)?;

    Ok(xs)
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
        Box::pin(get_network_interfaces(network_interfaces::get_interfaces))
    }
}
