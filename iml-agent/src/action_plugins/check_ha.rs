// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success};
use elementtree::Element;
use futures::{future, Future};
//use tracing_futures::Instrument;
use std::collections::HashMap;

// standard:provider:ocftype (e.g. ocf:heartbeat:ZFS, or stonith:fence_ipmilan)
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

impl From<ResourceAgentType> for String {
    fn from(agent: ResourceAgentType) -> Self {
        match agent.provider {
            Some(provider) => format!("{}:{}:{}", agent.standard, provider, agent.ocftype),
            None => format!("{}:{}", agent.standard, agent.ocftype),
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
    pub fn new(elem: &Element, group: Option<String>) -> AgentInfo {
        AgentInfo {
            agent: ResourceAgentType::new(
                elem.get_attr("class").unwrap().to_string(),
                elem.get_attr("provider").map(|s| s.to_string()),
                elem.get_attr("type").unwrap().to_string(),
            ),
            group: group,
            id: elem.get_attr("id").unwrap().to_string(),
            args: match elem.find("instance_attributes") {
                None => vec![],
                Some(e) => e
                    .find_all("nvpair")
                    .map(|nv| {
                        (
                            nv.get_attr("name").unwrap().to_string(),
                            nv.get_attr("value").unwrap().to_string(),
                        )
                    })
                    .collect(),
            }
            .iter()
            .cloned()
            .collect(),
        }
    }
}

pub fn check_ha(_: ()) -> impl Future<Item = Vec<AgentInfo>, Error = ImlAgentError> {
    cmd_output_success("cibadmin", &["--query", "--xpath", "//resources"]).and_then(|output| {
        match Element::from_reader(output.stdout.as_slice()) {
            Err(err) => future::err(ImlAgentError::XmlError(err)),
            Ok(elem) => future::ok(
                elem.find_all("group")
                    .flat_map(|g| {
                        let name = g.get_attr("id").unwrap();
                        g.find_all("primitive")
                            .map(move |p| AgentInfo::new(p, Some(name.clone().to_string())))
                    })
                    .chain(elem.find_all("primitive").map(|p| AgentInfo::new(p, None)))
                    .collect(),
            ),
        }
    })
}
