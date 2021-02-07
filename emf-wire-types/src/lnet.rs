// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{self, TableName},
    ComponentType, Label, ToComponentType,
};

#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Lnet {
    pub id: i32,
    pub host_id: i32,
    pub state: String,
    pub nids: Vec<i32>,
}

pub const LNET_TABLE_NAME: TableName = TableName("lnet");

impl db::Id for Lnet {
    fn id(&self) -> i32 {
        self.id
    }
}

impl db::Id for &Lnet {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for Lnet {
    fn label(&self) -> &str {
        "LNet"
    }
}

impl Label for &Lnet {
    fn label(&self) -> &str {
        "LNet"
    }
}

impl ToComponentType for Lnet {
    fn component_type(&self) -> ComponentType {
        ComponentType::Lnet
    }
}
