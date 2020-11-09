// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub(crate) mod corosync_conf;
pub(crate) mod pacemaker;

use crate::{
    agent_error::{ImlAgentError, RequiredError},
    high_availability::{crm_mon_cmd, read_crm_output},
};
use elementtree::Element;
use futures::{future::try_join_all, try_join};
use iml_cmd::{CheckedCommandExt, Command};
use iml_fs::file_exists;
use iml_wire_types::{
    ComponentState, ConfigState, PacemakerOperations, ResourceAgentInfo, ResourceAgentType,
    ServiceState,
};
use std::{collections::HashMap, ffi::OsStr, time::Duration};
use tokio::time::delay_for;

fn create(elem: &Element) -> ResourceAgentInfo {
    ResourceAgentInfo {
        agent: {
            ResourceAgentType::new(
                elem.get_attr("class"),
                elem.get_attr("provider"),
                elem.get_attr("type"),
            )
        },
        id: elem.get_attr("id").unwrap_or_default().to_string(),
        args: elem
            .find_all("instance_attributes")
            .map(|e| {
                e.find_all("nvpair").map(|nv| {
                    (
                        nv.get_attr("name").unwrap_or_default().to_string(),
                        nv.get_attr("value").unwrap_or_default().to_string(),
                    )
                })
            })
            .flatten()
            .collect(),
        ops: {
            // "stop"|"start"|"monitor" => (interval, timeout)
            let mut ops: HashMap<&str, (Option<String>, Option<String>)> = elem
                .find_all("operations")
                .map(|e| {
                    e.find_all("op").map(|nv| {
                        (
                            nv.get_attr("name").unwrap_or_default(),
                            (
                                nv.get_attr("interval").map(str::to_string),
                                nv.get_attr("timeout").map(str::to_string),
                            ),
                        )
                    })
                })
                .flatten()
                .collect();
            PacemakerOperations::new(
                ops.remove("start").map(|e| e.1).flatten(),
                ops.remove("monitor").map(|e| e.0).flatten(),
                ops.remove("stop").map(|e| e.1).flatten(),
            )
        },
    }
}

pub(crate) async fn crm_attribute(args: Vec<String>) -> Result<String, ImlAgentError> {
    let o = Command::new("crm_attribute")
        .args(args)
        .checked_output()
        .await?;

    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

pub(crate) async fn crm_resource<I, S>(args: I) -> Result<String, ImlAgentError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let o = Command::new("crm_resource")
        .args(args)
        .checked_output()
        .await?;

    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

pub(crate) async fn pcs(args: Vec<String>) -> Result<String, ImlAgentError> {
    let o = Command::new("pcs").args(args).checked_output().await?;

    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

async fn set_resource_role(resource: &str, running: bool) -> Result<(), ImlAgentError> {
    let args = &[
        "--resource",
        resource,
        "--set-parameter",
        "target-role",
        "--meta",
        "--parameter-value",
        if running { "Started" } else { "Stopped" },
    ];
    crm_resource(args).await?;
    Ok(())
}

async fn wait_resource(resource: &str, running: bool) -> Result<(), ImlAgentError> {
    let sec_to_wait = 300;
    let sec_delay = 2;
    let delay_duration = Duration::new(sec_delay, 0);
    for _ in 0..(sec_to_wait / sec_delay) {
        let output = crm_mon_cmd().checked_output().await?;

        let cluster = read_crm_output(&output.stdout)?;

        let check = if running { "Started" } else { "Stopped" };

        let mut stati = cluster
            .resources
            .into_iter()
            .filter_map(|r| {
                let id = r.id.split(':').next().unwrap_or("");
                if id == resource {
                    Some(r.role)
                } else {
                    None
                }
            })
            .peekable();
        if stati.peek() != None && stati.all(|s| s == check) {
            return Ok(());
        }
        delay_for(delay_duration).await;
    }
    Err(ImlAgentError::from(RequiredError(format!(
        "Waiting for resource {} of {} failed after {} sec",
        if running { "start" } else { "stop" },
        resource,
        sec_to_wait,
    ))))
}

fn process_resource(output: &[u8]) -> Result<ResourceAgentInfo, ImlAgentError> {
    let element = Element::from_reader(output)?;

    Ok(create(&element))
}

pub async fn get_ha_resource_list(_: ()) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
    let resources = match crm_resource(&["--list-raw"]).await {
        Ok(res) => res,
        Err(e) => {
            tracing::info!("Failed to get resource list: {:?}", e);
            return Ok(vec![]);
        }
    };

    let xs = resources
        .trim()
        .lines()
        .filter(|res| {
            // This filters out cloned resources which show up as:
            // clones-resource:0
            // clones-resource:1
            // ...
            // ":" is not valid in normal resource ids so only ":0" should be processed
            if let Some(n) = res.split(':').nth(1) {
                n.parse() == Ok(0)
            } else {
                true
            }
        })
        .map(|res| async move {
            let output = crm_resource(&["--query-xml", "--resource", res]).await?;
            if let Some(xml) = output.split("xml:").last() {
                process_resource(xml.as_bytes())
            } else {
                Err(ImlAgentError::MarkerNotFound)
            }
        });
    try_join_all(xs).await
}

async fn systemd_unit_servicestate(name: &str) -> Result<ServiceState, ImlAgentError> {
    let n = format!("{}.service", name);
    match iml_systemd::get_run_state(n).await {
        Ok(s) => Ok(ServiceState::Configured(s)),
        Err(err) => {
            tracing::debug!("Get Run State of {} failed: {:?}", name, err);
            Ok(ServiceState::Unconfigured)
        }
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
        let output = Command::new("corosync-cmapctl")
            .args(&["totem.interface.0.mcastaddr", "totem.interface.1.mcastaddr"])
            .checked_output()
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
        if resources.is_empty() {
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

pub async fn start_resource(resource: String) -> Result<(), ImlAgentError> {
    set_resource_role(&resource, true).await?;

    wait_resource(&resource, true).await?;
    Ok(())
}

pub async fn stop_resource(resource: String) -> Result<(), ImlAgentError> {
    set_resource_role(&resource, false).await?;

    wait_resource(&resource, false).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{process_resource, PacemakerOperations, ResourceAgentInfo, ResourceAgentType};
    use std::collections::HashMap;

    #[test]
    fn test_ha_only_fence_chroma() {
        let testxml = include_bytes!("fixtures/crm-resource-chroma-stonith.xml");

        assert_eq!(
            process_resource(testxml).unwrap(),
            ResourceAgentInfo {
                agent: ResourceAgentType::new("stonith", None, "fence_chroma"),
                id: "st-fencing".to_string(),
                args: HashMap::new(),
                ops: PacemakerOperations::new(None, None, None),
            }
        );
    }

    #[test]
    fn test_iml() {
        let testxml = include_bytes!("fixtures/crm-resource-iml-mgs.xml");

        let r1 = ResourceAgentInfo {
            agent: ResourceAgentType::new("ocf", Some("lustre"), "Lustre"),
            id: "MGS".to_string(),
            args: vec![
                ("mountpoint", "/mnt/MGS"),
                (
                    "target",
                    "/dev/disk/by-id/scsi-36001405c20616f7b8b2492d8913a4d24",
                ),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
            ops: PacemakerOperations::new(
                Some("300s".to_string()),
                Some("20s".to_string()),
                Some("300s".to_string()),
            ),
        };

        assert_eq!(process_resource(testxml).unwrap(), r1);
    }

    #[test]
    fn test_es_ost() {
        let testxml = include_bytes!("fixtures/crm-resource-es-ost.xml");

        let r1 = ResourceAgentInfo {
            agent: ResourceAgentType::new("ocf", Some("ddn"), "lustre-server"),
            id: "ost0001-es01a".to_string(),
            args: vec![
                ("lustre_resource_type", "ost"),
                ("manage_directory", "1"),
                ("device", "/dev/ddn/es01a_ost0001"),
                ("directory", "/lustre/es01a/ost0001"),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
            ops: PacemakerOperations::new(
                Some("450".to_string()),
                Some("30".to_string()),
                Some("300".to_string()),
            ),
        };

        assert_eq!(process_resource(testxml).unwrap(), r1);
    }
}
