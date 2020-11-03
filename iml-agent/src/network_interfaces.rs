// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError, network_interface::parse as parse_interfaces,
    network_interface_stats,
};
use iml_cmd::{CheckedCommandExt, Command};
use iml_wire_types::NetworkInterface;

fn ip_addr_cmd() -> Command {
    let mut cmd = Command::new("ip");

    cmd.arg("address");

    cmd
}

fn get_net_stats_cmd() -> Command {
    let mut cmd = Command::new("cat");

    cmd.arg("/proc/net/dev");

    cmd
}

pub async fn get_interfaces() -> Result<Vec<NetworkInterface>, ImlAgentError> {
    let net_stats = get_net_stats_cmd().checked_output().await?;

    let net_stats = std::str::from_utf8(&net_stats.stdout)?;

    let net_stats = network_interface_stats::parse(net_stats)?;

    let network_interfaces = ip_addr_cmd().checked_output().await?;

    let network_interfaces = std::str::from_utf8(&network_interfaces.stdout)?;

    parse_interfaces(network_interfaces, net_stats)
}
