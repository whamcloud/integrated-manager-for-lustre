// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError, network_interface::parse as parse_interfaces,
    network_interface_stats,
};
use iml_cmd::{CheckedCommandExt, Command};
use iml_wire_types::{LNet, LNetState, NetworkInterface};

fn ip_addr_cmd() -> Command {
    let mut cmd = Command::new("ip");

    cmd.kill_on_drop(true);
    cmd.arg("address");

    cmd
}

fn get_net_stats_cmd() -> Command {
    let mut cmd = Command::new("cat");

    cmd.kill_on_drop(true);
    cmd.arg("/proc/net/dev");

    cmd
}

fn get_lnet_data_cmd() -> Command {
    let mut cmd = Command::new("lnetctl");

    cmd.kill_on_drop(true);
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

async fn get_lnet_state() -> Result<LNetState, ImlAgentError> {
    let loaded: bool = Command::new("udevadm")
        .args(&["info", "--path", "/sys/module/lnet"])
        .status()
        .await?
        .success();

    if !loaded {
        Ok(LNetState::Unloaded)
    } else {
        let up = Command::new("lnetctl")
            .args(&["net", "show"])
            .status()
            .await?
            .success();

        match up {
            true => Ok(LNetState::Up),
            false => Ok(LNetState::Down),
        }
    }
}

pub async fn get_lnet_data() -> Result<LNet, ImlAgentError> {
    let r = get_lnet_data_cmd().checked_output().await;
    let state = get_lnet_state().await.unwrap_or_default();

    match r {
        Ok(x) => {
            tracing::debug!("Parcing received lnet data.");
            let lnet_data = std::str::from_utf8(&x.stdout)?.trim();

            let mut lnet = if lnet_data.is_empty() {
                LNet::default()
            } else {
                serde_yaml::from_str(lnet_data).unwrap_or_default()
            };

            lnet.state = state;

            Ok(lnet)
        }
        Err(_) => {
            // This branch will be hit if `lnetctl net show` returns a non-zero value. This happens when
            // lnet has been unconfigured but the module is still loaded.
            let mut lnet = LNet::default();
            lnet.state = state;

            Ok(lnet)
        }
    }
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

        let mut yaml: LNet = serde_yaml::from_str(data).unwrap();
        yaml.state = LNetState::Up;

        insta::with_settings!({sort_maps => true}, {
            insta::assert_json_snapshot!(yaml)
        });
    }

    #[test]
    fn test_equality() {
        let data1 = r#"net:
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

        let data2 = r#"net:
    - net type: lo
      local NI(s):
        - nid: 0@lo
          status: up
    - net type: o2ib
      local NI(s):
        - nid: 172.16.0.28@o2ib
          status: up
          interfaces:
            0: ib5
            1: ib4
            2: ib1
        - nid: 172.16.0.24@o2ib
          status: down
          interfaces:
            0: ib3
            1: ib0
    - net type: tcp
      local NI(s):
        - nid: 10.73.20.21@tcp
          status: up
          interfaces:
            0: eth2
            1: eth1
    "#;

        let mut data1: LNet = serde_yaml::from_str(data1).unwrap();
        data1.state = LNetState::Up;

        let mut data2: LNet = serde_yaml::from_str(data2).unwrap();
        data2.state = LNetState::Up;

        assert_eq!(data1, data2);
    }

    #[test]
    fn test_json_data() {
        let data = r#"{"net":[{"net type":"lo","local NI(s)":[{"nid":"0@lo","status":"up","interfaces":null}]},{"net type":"tcp","local NI(s)":[{"nid":"10.73.20.11@tcp","status":"up","interfaces":["eth1"]}]}],"state":"Up"}"#;
        let data: LNet = serde_json::from_str(data).unwrap();

        insta::with_settings!({sort_maps => true}, {
            insta::assert_json_snapshot!(data)
        });
    }
}
