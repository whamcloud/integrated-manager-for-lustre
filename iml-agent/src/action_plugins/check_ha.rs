// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success};
use elementtree::Element;
use futures::Future;
use std::collections::HashMap;
use std::fmt;
use tracing::{span, Level};
use tracing_futures::Instrument;

/// standard:provider:ocftype (e.g. ocf:heartbeat:ZFS, or stonith:fence_ipmilan)
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq)]
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

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq)]
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
            group: group,
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

fn do_check_ha(output: &[u8]) -> Result<Vec<AgentInfo>, ImlAgentError> {
    match Element::from_reader(output) {
        Err(err) => Err(ImlAgentError::XmlError(err)),
        Ok(elem) => Ok(elem
            .find_all("group")
            .flat_map(|g| {
                let name = g.get_attr("id").unwrap_or("").to_string();
                g.find_all("primitive")
                    .map(move |p| AgentInfo::create(p, Some(name.clone())))
            })
            .chain(
                elem.find_all("primitive")
                    .map(|p| AgentInfo::create(p, None)),
            )
            .collect()),
    }
}

pub fn check_ha(_: ()) -> impl Future<Item = Vec<AgentInfo>, Error = ImlAgentError> {
    cmd_output_success("cibadmin", &["--query", "--xpath", "//resources"])
        .instrument(span!(Level::INFO, "Read cib"))
        .and_then(|output| do_check_ha(&output.stdout.as_slice()))
}

#[cfg(test)]
mod tests {
    use super::{do_check_ha, AgentInfo, ResourceAgentType};
    use crate::agent_error;
    use std::collections::HashMap;

    #[test]
    fn test_ha_only_fence_chroma() {
        let testxml = r#"<resources>
  <primitive class="stonith" id="st-fencing" type="fence_chroma"/>
</resources>
"#;
        assert_eq!(
            do_check_ha(&testxml.as_bytes()).unwrap(),
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

        assert_eq!(do_check_ha(&testxml.as_bytes()).unwrap(), vec![a1, a2, a3]);
    }
}
