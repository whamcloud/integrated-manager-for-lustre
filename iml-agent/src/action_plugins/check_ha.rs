// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success};
use elementtree::Element;
use futures::{future, Future};
use std::collections::HashMap;
use std::fmt;
use tracing::{span, Level};
use tracing_futures::Instrument;

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

pub fn check_ha(_: ()) -> impl Future<Item = Vec<AgentInfo>, Error = ImlAgentError> {
    cmd_output_success("cibadmin", &["--query", "--xpath", "//resources"])
        .instrument(span!(Level::INFO, "Read cib"))
        .and_then(|output| {
            // This cannot split between map/map_err because Element does not implement Send
            match Element::from_reader(output.stdout.as_slice()) {
                Err(err) => future::err(ImlAgentError::XmlError(err)),
                Ok(elem) => future::ok(
                    elem.find_all("group")
                        .flat_map(|g| {
                            let name = g.get_attr("id").unwrap_or("").to_string();
                            g.find_all("primitive")
                                .map(move |p| AgentInfo::create(p, Some(name.clone())))
                        })
                        .chain(
                            elem.find_all("primitive")
                                .map(|p| AgentInfo::create(p, None)),
                        )
                        .collect(),
                ),
            }
        })
        .from_err()
}
