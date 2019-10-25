// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success, systemd};
use elementtree::Element;
use futures::try_join;
use iml_wire_types::{ComponentState, ConfigState, ServiceState};
use std::{collections::HashMap, fmt, str};
use tokio::fs::File;

/// standard:provider:ocftype (e.g. ocf:heartbeat:ZFS, or stonith:fence_ipmilan)
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
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

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
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

pub async fn get_ha_resource_list(_: ()) -> Result<Vec<AgentInfo>, ImlAgentError> {
    let output = cmd_output_success("cibadmin", vec!["--query", "--xpath", "//resources"]).await?;

    // This cannot split between map/map_err because Element does not implement Send
    let elem = Element::from_reader(output.stdout.as_slice())?;
    Ok(elem
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
        .collect())
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
    let f = File::open(path.to_string()).await;
    tracing::debug!("Checking file {} : {:?}", path, f);
    match f {
        Ok(_) => o.status.success(),
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
