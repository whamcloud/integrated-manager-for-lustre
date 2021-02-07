// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::{DateTime, Utc};

use crate::{
    db::{self, TableName},
    ComponentType, Label, ToComponentType,
};

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
