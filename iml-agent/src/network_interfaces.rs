// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError, network_interface::parse as parse_interfaces,
    network_interface_stats,
};
use iml_cmd::{CheckedCommandExt, CmdError, Command};
use iml_wire_types::{LNet, NetworkInterface};
use std::io;

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

fn get_lnet_data_cmd() -> Command {
    let mut cmd = Command::new("lnetctl");

    cmd.args(&["net", "show"]);

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

pub async fn get_lnet_data() -> Result<LNet, ImlAgentError> {
    let r = get_lnet_data_cmd().checked_output().await;

    let x = match r {
        Ok(x) => Ok(x.stdout),
        Err(CmdError::Io(ref err)) if err.kind() == io::ErrorKind::NotFound => {
            tracing::debug!("lnetctl was not found. Will not send net data");

            Ok(vec![])
        }
        Err(e) => Err(e),
    }?;

    let lnet_data = std::str::from_utf8(&x)?.trim();

    if lnet_data.is_empty() {
        return Ok(LNet::default());
    };

    let x: LNet = serde_yaml::from_str(lnet_data)?;

    Ok(x)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_lnetctl_net_show_output() {
        let data = r#"net:
    - net type: lo
      local NI(s):
        - nid: 0@lo
          status: up
    - net type: tcp
      local NI(s):
        - nid: 10.73.20.21@tcp
          status: up
          interfaces:
              0: eth1
              1: eth2
    - net type: o2ib
      local NI(s):
        - nid: 172.16.0.24@o2ib
          status: down
          interfaces:
              0: ib0
              1: ib3
        - nid: 172.16.0.28@o2ib
          status: up
          interfaces:
              0: ib1
              1: ib4
              2: ib5"#;

        let yaml: LNet = serde_yaml::from_str(data).unwrap();

        insta::with_settings!({sort_maps => true}, {
            insta::assert_json_snapshot!(yaml)
        });
    }
}
