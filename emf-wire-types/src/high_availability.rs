// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::{
    collections::HashMap,
    convert::TryFrom,
    fmt::{self, Display},
    io,
};

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub enum NodeType {
    Unknown,
    Member,
    Remote,
    Ping,
}

impl TryFrom<&str> for NodeType {
    type Error = io::Error;

    fn try_from(x: &str) -> Result<Self, Self::Error> {
        match x {
            "unknown" => Ok(Self::Unknown),
            "member" => Ok(Self::Member),
            "remote" => Ok(Self::Remote),
            "ping" => Ok(Self::Ping),
            x => Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                format!("Invalid node type {}", x),
            )),
        }
    }
}

impl Display for NodeType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            NodeType::Unknown => "unknown",
            NodeType::Member => "member",
            NodeType::Remote => "remote",
            NodeType::Ping => "ping",
        };

        write!(f, "{}", x)
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct Node {
    pub name: String,
    pub id: String,
    pub online: bool,
    pub standby: bool,
    pub standby_onfail: bool,
    pub maintenance: bool,
    pub pending: bool,
    pub unclean: bool,
    pub shutdown: bool,
    pub expected_up: bool,
    pub is_dc: bool,
    pub resources_running: u32,
    pub r#type: NodeType,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct Resource {
    pub id: String,
    pub resource_agent: String,
    pub role: String,
    pub active: bool,
    pub orphaned: bool,
    pub managed: bool,
    pub failed: bool,
    pub failure_ignored: bool,
    pub nodes_running_on: u32,
    pub active_node_name: Option<String>,
    pub active_node_id: Option<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct Ban {
    pub id: String,
    pub resource: String,
    pub node: String,
    pub weight: i32,
    pub master_only: bool,
}

#[derive(Debug, Default, serde::Serialize, serde::Deserialize)]
pub struct Cluster {
    pub nodes: Vec<Node>,
    pub resources: Vec<Resource>,
    pub bans: Vec<Ban>,
    pub resource_mounts: HashMap<String, String>,
}
