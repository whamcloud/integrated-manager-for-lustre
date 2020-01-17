// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, systemd};
use elementtree::Element;
use futures::try_join;
use iml_cmd::cmd_output_success;
use iml_wire_types::{
    ComponentState, ConfigState, ResourceAgentInfo, ResourceAgentType, ServiceState,
};
use std::collections::HashMap;
use tokio::fs::metadata;

fn create<'a>(elem: &Element, group: impl Into<Option<&'a str>>) -> ResourceAgentInfo {
    ResourceAgentInfo {
        agent: ResourceAgentType::new(
            elem.get_attr("class"),
            elem.get_attr("provider"),
            elem.get_attr("type"),
        ),
        group: group.into().map(str::to_string),
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

fn process_resource_list(output: &[u8]) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
    let element = Element::from_reader(output)?;

    Ok(element
        .find_all("group")
        .flat_map(|g| {
            g.find_all("primitive")
                .map(move |p| create(p, g.get_attr("id").unwrap_or_default()))
        })
        .chain(element.find_all("primitive").map(|p| create(p, None)))
        .collect())
}

pub async fn get_ha_resource_list(_: ()) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
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
    use super::{process_resource_list, ResourceAgentInfo, ResourceAgentType};
    use std::collections::HashMap;

    #[test]
    fn test_ha_only_fence_chroma() {
        let testxml = r#"<resources>
  <primitive class="stonith" id="st-fencing" type="fence_chroma"/>
</resources>
"#
        .as_bytes();
        assert_eq!(
            process_resource_list(&testxml).unwrap(),
            vec![ResourceAgentInfo {
                agent: ResourceAgentType::new("stonith", None, "fence_chroma"),
                group: None,
                id: "st-fencing".to_string(),
                args: HashMap::new()
            }]
        );
    }

    #[test]
    fn test_ha_mixed_mode() {
        let testxml = include_bytes!("snapshots/check_ha_test_mixed_mode.xml");

        let mut a1 = ResourceAgentInfo {
            agent: ResourceAgentType::new("ocf", Some("chroma"), "ZFS"),
            group: Some("group-MGS_695ee8".to_string()),
            id: "MGS_695ee8-zfs".to_string(),
            args: HashMap::new(),
        };
        a1.args.insert("pool".to_string(), "MGS".to_string());
        let mut a2 = ResourceAgentInfo {
            agent: ResourceAgentType::new("ocf", Some("lustre"), "Lustre"),
            group: Some("group-MGS_695ee8".to_string()),
            id: "MGS_695ee8".to_string(),
            args: HashMap::new(),
        };
        a2.args.insert("target".to_string(), "MGS/MGS".to_string());
        a2.args
            .insert("mountpoint".to_string(), "/mnt/MGS".to_string());
        let mut a3 = ResourceAgentInfo {
            agent: ResourceAgentType::new("ocf", Some("lustre"), "Lustre"),
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

        assert_eq!(process_resource_list(testxml).unwrap(), vec![a1, a2, a3]);
    }
}
