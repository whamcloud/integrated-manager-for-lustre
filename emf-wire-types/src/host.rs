// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{self, TableName},
    ComponentType, Label, ToComponentType,
};
use chrono::{DateTime, Utc};
use std::str::FromStr;

#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct Host {
    pub id: i32,
    pub state: String,
    pub fqdn: String,
    pub machine_id: String,
    pub boot_time: DateTime<Utc>,
}

impl db::Id for Host {
    fn id(&self) -> i32 {
        self.id
    }
}

impl db::Id for &Host {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for Host {
    fn label(&self) -> &str {
        &self.fqdn
    }
}

impl ToComponentType for Host {
    fn component_type(&self) -> ComponentType {
        ComponentType::Host
    }
}

pub const HOST_TABLE_NAME: TableName = TableName("host");

/// The primary purpose of this host
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[derive(Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Flavor {
    Server,
    Client,
    Ubuntu,
    UbuntuDgx,
}

impl FromStr for Flavor {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "server" => Ok(Self::Server),
            "client" => Ok(Self::Client),
            "ubuntu" => Ok(Self::Ubuntu),
            "ubuntudgx" | "ubuntu_dgx" => Ok(Self::UbuntuDgx),
            x => Err(format!("Unexpected '{}'", x)),
        }
    }
}
