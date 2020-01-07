// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success};
use elementtree::Element;
use std::collections::HashMap;
use iml_wire_types::{ResourceAgentInfo, ResourceAgentType};

fn create(elem: &Element, group: Option<String>) -> ResourceAgentInfo {
    ResourceAgentInfo {
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

fn process_resources(xml: &[u8]) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
    // This cannot split between map/map_err because Element does not implement Send
    match Element::from_reader(xml) {
        Err(err) => Err(ImlAgentError::XmlError(err)),
        Ok(elem) => Ok(
            elem.find_all("group")
                .flat_map(|g| {
                    let name = g.get_attr("id").unwrap_or("").to_string();
                    g.find_all("primitive")
                        .map(move |p| create(p, Some(name.clone())))
                })
                .chain(
                    elem.find_all("primitive")
                        .map(|p| create(p, None)),
                )
                .collect(),
        ),
    }
}

pub async fn check_ha(_: ()) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
    cmd_output_success("cibadmin", vec!["--query", "--xpath", "//resources"])
        .await
        .and_then(|output| process_resources(output.stdout.as_slice()))
}

#[cfg(test)]
mod tests {
    use super::process_resources;

    #[test]
    fn test_good() {
        let testxml = r#"<resources>
  <primitive class="stonith" id="st-fencing" type="fence_chroma"/>
  <primitive class="ocf" id="MGS_b8aa2b" provider="lustre" type="Lustre">
    <instance_attributes id="MGS_b8aa2b-instance_attributes">
      <nvpair id="MGS_b8aa2b-instance_attributes-instance_attributes-mountpoint" name="mountpoint" value="/mnt/MGS"/>
      <nvpair id="MGS_b8aa2b-instance_attributes-instance_attributes-target" name="target" value="/dev/disk/by-id/scsi-36001405c20616f7b8b2492d8913a4d24"/>
    </instance_attributes>
    <operations>
      <op id="MGS_b8aa2b-start-interval-0s" interval="0s" name="start" timeout="300s"/>
      <op id="MGS_b8aa2b-stop-interval-0s" interval="0s" name="stop" timeout="300s"/>
      <op id="MGS_b8aa2b-monitor-interval-20s" interval="20s" name="monitor" timeout="300s"/>
    </operations>
    <meta_attributes id="MGS_b8aa2b-meta_attributes">
      <nvpair id="MGS_b8aa2b-meta_attributes-meta_attributes-target_role" name="target_role" value="Stopped"/>
      <nvpair id="MGS_b8aa2b-meta_attributes-target-role" name="target-role" value="Started"/>
    </meta_attributes>
  </primitive>
  <group id="group-fs10-MDT0000_c81867">
    <primitive class="ocf" id="fs10-MDT0000_c81867" provider="lustre" type="Lustre">
      <instance_attributes id="fs10-MDT0000_c81867-instance_attributes">
        <nvpair id="fs10-MDT0000_c81867-instance_attributes-instance_attributes-mountpoint" name="mountpoint" value="/mnt/fs10-MDT0000"/>
        <nvpair id="fs10-MDT0000_c81867-instance_attributes-instance_attributes-target" name="target" value="/dev/disk/by-id/scsi-3600140562d7cc2e77b040ae861a491f3"/>
      </instance_attributes>
      <operations>
        <op id="fs10-MDT0000_c81867-start-interval-0s" interval="0s" name="start" timeout="300s"/>
        <op id="fs10-MDT0000_c81867-stop-interval-0s" interval="0s" name="stop" timeout="300s"/>
        <op id="fs10-MDT0000_c81867-monitor-interval-20s" interval="20s" name="monitor" timeout="300s"/>
      </operations>
      <meta_attributes id="fs10-MDT0000_c81867-meta_attributes">
        <nvpair id="fs10-MDT0000_c81867-meta_attributes-meta_attributes-target_role" name="target_role" value="Stopped"/>
        <nvpair id="fs10-MDT0000_c81867-meta_attributes-target-role" name="target-role" value="Started"/>
      </meta_attributes>
    </primitive>
    <primitive class="systemd" id="test" type="httpd">
      <operations>
        <op id="test-monitor-interval-60" interval="60" name="monitor" timeout="100"/>
        <op id="test-start-interval-0s" interval="0s" name="start" timeout="100"/>
        <op id="test-stop-interval-0s" interval="0s" name="stop" timeout="100"/>
      </operations>
    </primitive>
  </group>
  <group id="group-fs11-MDT0000_13a57f">
    <primitive class="ocf" id="fs11-MDT0000_13a57f-zfs" provider="chroma" type="ZFS">
      <instance_attributes id="fs11-MDT0000_13a57f-zfs-instance_attributes">
        <nvpair id="fs11-MDT0000_13a57f-zfs-instance_attributes-instance_attributes-pool" name="pool" value="mdt10"/>
      </instance_attributes>
      <operations>
        <op id="fs11-MDT0000_13a57f-zfs-start-interval-0s" interval="0s" name="start" timeout="60s"/>
        <op id="fs11-MDT0000_13a57f-zfs-stop-interval-0s" interval="0s" name="stop" timeout="60s"/>
        <op id="fs11-MDT0000_13a57f-zfs-monitor-interval-5s" interval="5s" name="monitor" timeout="30s"/>
      </operations>
    </primitive>
    <primitive class="ocf" id="fs11-MDT0000_13a57f" provider="lustre" type="Lustre">
      <instance_attributes id="fs11-MDT0000_13a57f-instance_attributes">
        <nvpair id="fs11-MDT0000_13a57f-instance_attributes-instance_attributes-mountpoint" name="mountpoint" value="/mnt/fs11-MDT0000"/>
        <nvpair id="fs11-MDT0000_13a57f-instance_attributes-instance_attributes-target" name="target" value="mdt10/fs11-MDT0000"/>
      </instance_attributes>
      <operations>
        <op id="fs11-MDT0000_13a57f-start-interval-0s" interval="0s" name="start" timeout="300s"/>
        <op id="fs11-MDT0000_13a57f-stop-interval-0s" interval="0s" name="stop" timeout="300s"/>
        <op id="fs11-MDT0000_13a57f-monitor-interval-20s" interval="20s" name="monitor" timeout="300s"/>
      </operations>
    </primitive>
    <meta_attributes id="group-fs11-MDT0000_13a57f-meta_attributes">
      <nvpair id="group-fs11-MDT0000_13a57f-meta_attributes-meta_attributes-target_role" name="target_role" value="Stopped"/>
    </meta_attributes>
  </group>
</resources>
"#.as_bytes();

        let res = process_resources(testxml).unwrap();

        assert_eq!(res.len(), 6);
    }
}
