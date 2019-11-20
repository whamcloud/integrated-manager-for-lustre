// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success, systemd};
use elementtree::Element;
use futures::try_join;
use iml_wire_types::{ComponentState, ConfigState, ServiceState};
use std::{collections::HashMap, fmt, str};
use tokio::fs::metadata;

/// standard:provider:ocftype (e.g. ocf:heartbeat:ZFS, or stonith:fence_ipmilan)
#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct ResourceAgentType {
    pub standard: String,         // e.g. ocf, lsb, stonith, etc..
    pub provider: Option<String>, // e.g. heartbeat, lustre, chroma
    pub ocftype: String,          // e.g. Lustre, ZFS
}

impl ResourceAgentType {
    pub fn new(standard: String, provider: Option<String>, ocftype: String) -> Self {
        ResourceAgentType {
            standard,
            provider,
            ocftype,
        }
    }
}

impl fmt::Display for ResourceAgentType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.provider {
            Some(provider) => write!(f, "{}:{}:{}", self.standard, provider, self.ocftype),
            None => write!(f, "{}:{}", self.standard, self.ocftype),
        }
    }
}

impl PartialEq<String> for ResourceAgentType {
    fn eq(&self, other: &String) -> bool {
        self.to_string() == *other
    }
}

impl PartialEq<&str> for ResourceAgentType {
    fn eq(&self, other: &&str) -> bool {
        self.to_string() == *other
    }
}

#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct AgentInfo {
    pub agent: ResourceAgentType,
    pub group: Option<String>,
    pub id: String,
    pub args: HashMap<String, String>,
}

impl AgentInfo {
    pub fn create(elem: &Element, group: Option<String>) -> Self {
        AgentInfo {
            agent: ResourceAgentType::new(
                elem.get_attr("class").unwrap_or("").to_string(),
                elem.get_attr("provider").map(|s| s.to_string()),
                elem.get_attr("type").unwrap_or("").to_string(),
            ),
            group,
            id: elem.get_attr("id").unwrap_or("").to_string(),
            args: match elem.find("instance_attributes") {
                None => HashMap::new(),
                Some(e) => e
                    .find_all("nvpair")
                    .map(|nv| {
                        (
                            nv.get_attr("name").unwrap_or("").to_string(),
                            nv.get_attr("value").unwrap_or("").to_string(),
                        )
                    })
                    .collect(),
            },
        }
    }
}

fn process_resource_list(output: &[u8]) -> Result<Vec<AgentInfo>, ImlAgentError> {
    let element = Element::from_reader(output)?;

    Ok(element
        .find_all("group")
        .flat_map(|g| {
            let name = g.get_attr("id").unwrap_or("").to_string();
            g.find_all("primitive")
                .map(move |p| AgentInfo::create(p, Some(name.clone())))
        })
        .chain(
            element
                .find_all("primitive")
                .map(|p| AgentInfo::create(p, None)),
        )
        .collect())
}

pub async fn get_ha_resource_list(_: ()) -> Result<Vec<AgentInfo>, ImlAgentError> {
    let resources =
        cmd_output_success("cibadmin", vec!["--query", "--xpath", "//resources"]).await?;

    process_resource_list(resources.stdout.as_slice())
}

async fn systemd_unit_servicestate(name: &str) -> Result<ServiceState, ImlAgentError> {
    let n = format!("{}.service", name);
    match systemd::get_run_state(n).await {
        Ok(s) => Ok(ServiceState::Configured(s)),
        Err(err) => {
            tracing::debug!("Get Run State of {} failed: {:?}", name, err);
            Ok(ServiceState::Unconfigured)
        }
    }
}

async fn file_exists(path: &str) -> bool {
    let f = metadata(path).await;
    tracing::debug!("Checking file {} : {:?}", path, f);
    match f {
        Ok(m) => m.is_file(),
        Err(_) => false,
    }
}

async fn check_corosync() -> Result<ComponentState<bool>, ImlAgentError> {
    let mut corosync = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/etc/corosync/corosync.conf").await {
        let expected = r#"totem.interface.0.mcastaddr (str) = 226.94.0.1
totem.interface.1.mcastaddr (str) = 226.94.1.1
"#
        .as_bytes();
        let output = cmd_output_success(
            "corosync-cmapctl",
            vec!["totem.interface.0.mcastaddr", "totem.interface.1.mcastaddr"],
        )
        .await?;

        corosync.config = if output.stdout == expected {
            ConfigState::IML
        } else {
            ConfigState::Unknown
        };
        corosync.service = systemd_unit_servicestate("corosync").await?;
        // @@ check corosync setup
    }

    Ok(corosync)
}

async fn check_pacemaker() -> Result<ComponentState<bool>, ImlAgentError> {
    let mut pacemaker = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/var/lib/pacemaker/cib/cib.xml").await {
        pacemaker.service = systemd_unit_servicestate("pacemaker").await?;
        let resources = get_ha_resource_list(()).await?;
        if resources.len() == 0 {
            pacemaker.config = ConfigState::Default;
        } else {
            pacemaker.config = ConfigState::Unknown;
        }
        for res in resources {
            if res.id == "st-fencing" && res.agent.ocftype == "fence_chroma" {
                pacemaker.config = ConfigState::IML;
                break;
            }
        }
    }

    Ok(pacemaker)
}

async fn check_pcs() -> Result<ComponentState<bool>, ImlAgentError> {
    let mut pcs = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/var/lib/pcsd/tokens").await {
        pcs.config = ConfigState::IML;
        pcs.service = systemd_unit_servicestate("pcsd").await?;
    }

    Ok(pcs)
}

pub async fn check_ha(
    _: (),
) -> Result<
    (
        ComponentState<bool>,
        ComponentState<bool>,
        ComponentState<bool>,
    ),
    ImlAgentError,
> {
    let corosync = check_corosync();
    let pacemaker = check_pacemaker();
    let pcs = check_pcs();

    try_join!(corosync, pacemaker, pcs)
}

#[cfg(test)]
mod tests {
    use super::{process_resource_list, AgentInfo, ResourceAgentType};
    use std::collections::HashMap;

    #[test]
    fn test_ha_only_fence_chroma() {
        let testxml = r#"<resources>
  <primitive class="stonith" id="st-fencing" type="fence_chroma"/>
</resources>
"#;
        assert_eq!(
            process_resource_list(&testxml.as_bytes()).unwrap(),
            vec![AgentInfo {
                agent: ResourceAgentType::new(
                    "stonith".to_string(),
                    None,
                    "fence_chroma".to_string()
                ),
                group: None,
                id: "st-fencing".to_string(),
                args: HashMap::new()
            }]
        );
    }

    #[test]
    fn test_ha_mixed_mode() {
        let testxml = r#"<resources>
  <group id="group-MGS_695ee8">
    <primitive class="ocf" id="MGS_695ee8-zfs" provider="chroma" type="ZFS">
      <instance_attributes id="MGS_695ee8-zfs-instance_attributes">
        <nvpair id="MGS_695ee8-zfs-instance_attributes-instance_attributes-pool" name="pool" value="MGS"/>
      </instance_attributes>
      <operations>
        <op id="MGS_695ee8-zfs-start-interval-0s" interval="0s" name="start" timeout="60s"/>
        <op id="MGS_695ee8-zfs-stop-interval-0s" interval="0s" name="stop" timeout="60s"/>
        <op id="MGS_695ee8-zfs-monitor-interval-5s" interval="5s" name="monitor" timeout="30s"/>
      </operations>
    </primitive>
    <primitive class="ocf" id="MGS_695ee8" provider="lustre" type="Lustre">
      <instance_attributes id="MGS_695ee8-instance_attributes">
        <nvpair id="MGS_695ee8-instance_attributes-instance_attributes-mountpoint" name="mountpoint" value="/mnt/MGS"/>
        <nvpair id="MGS_695ee8-instance_attributes-instance_attributes-target" name="target" value="MGS/MGS"/>
      </instance_attributes>
      <operations>
        <op id="MGS_695ee8-start-interval-0s" interval="0s" name="start" timeout="300s"/>
        <op id="MGS_695ee8-stop-interval-0s" interval="0s" name="stop" timeout="300s"/>
        <op id="MGS_695ee8-monitor-interval-20s" interval="20s" name="monitor" timeout="300s"/>
      </operations>
    </primitive>
    <meta_attributes id="group-MGS_695ee8-meta_attributes">
      <nvpair id="group-MGS_695ee8-meta_attributes-meta_attributes-target_role" name="target_role" value="Stopped"/>
    </meta_attributes>
  </group>
  <primitive class="ocf" id="fs21-MDT0000_f61385" provider="lustre" type="Lustre">
    <instance_attributes id="fs21-MDT0000_f61385-instance_attributes">
      <nvpair id="fs21-MDT0000_f61385-instance_attributes-instance_attributes-mountpoint" name="mountpoint" value="/mnt/fs21-MDT0000"/>
      <nvpair id="fs21-MDT0000_f61385-instance_attributes-instance_attributes-target" name="target" value="/dev/disk/by-id/scsi-36001405da302b267f944aeaaadb95af9"/>
    </instance_attributes>
    <operations>
      <op id="fs21-MDT0000_f61385-start-interval-0s" interval="0s" name="start" timeout="300s"/>
      <op id="fs21-MDT0000_f61385-stop-interval-0s" interval="0s" name="stop" timeout="300s"/>
      <op id="fs21-MDT0000_f61385-monitor-interval-20s" interval="20s" name="monitor" timeout="300s"/>
    </operations>
    <meta_attributes id="fs21-MDT0000_f61385-meta_attributes">
      <nvpair id="fs21-MDT0000_f61385-meta_attributes-meta_attributes-target_role" name="target_role" value="Stopped"/>
    </meta_attributes>
  </primitive>
</resources>
"#;

        let mut a1 = AgentInfo {
            agent: ResourceAgentType::new(
                "ocf".to_string(),
                Some("chroma".to_string()),
                "ZFS".to_string(),
            ),
            group: Some("group-MGS_695ee8".to_string()),
            id: "MGS_695ee8-zfs".to_string(),
            args: HashMap::new(),
        };
        a1.args.insert("pool".to_string(), "MGS".to_string());
        let mut a2 = AgentInfo {
            agent: ResourceAgentType::new(
                "ocf".to_string(),
                Some("lustre".to_string()),
                "Lustre".to_string(),
            ),
            group: Some("group-MGS_695ee8".to_string()),
            id: "MGS_695ee8".to_string(),
            args: HashMap::new(),
        };
        a2.args.insert("target".to_string(), "MGS/MGS".to_string());
        a2.args
            .insert("mountpoint".to_string(), "/mnt/MGS".to_string());
        let mut a3 = AgentInfo {
            agent: ResourceAgentType::new(
                "ocf".to_string(),
                Some("lustre".to_string()),
                "Lustre".to_string(),
            ),
            group: None,
            id: "fs21-MDT0000_f61385".to_string(),
            args: HashMap::new(),
        };
        a3.args.insert(
            "target".to_string(),
            "/dev/disk/by-id/scsi-36001405da302b267f944aeaaadb95af9".to_string(),
        );
        a3.args
            .insert("mountpoint".to_string(), "/mnt/fs21-MDT0000".to_string());

        assert_eq!(
            process_resource_list(&testxml.as_bytes()).unwrap(),
            vec![a1, a2, a3]
        );
    }
}
