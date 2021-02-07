// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{Id, TableName},
    ComponentType, FsType, Label, ToComponentType,
};

#[derive(serde::Deserialize, serde::Serialize, Clone, Copy, Debug, Eq, PartialEq)]
#[serde(rename_all = "UPPERCASE")]
pub enum TargetKind {
    Mgt,
    Mdt,
    Ost,
}

fn get_kind(x: &str) -> TargetKind {
    match x {
        "MGS" => TargetKind::Mgt,
        name if name.contains("-MDT") => TargetKind::Mdt,
        _ => TargetKind::Ost,
    }
}

/// A Lustre Target
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct TargetRecord {
    pub id: i32,
    /// The target's state. One of "mounted" or "unmounted"
    pub state: String,
    /// The target name
    pub name: String,
    /// The device path used to create the target mount
    pub dev_path: Option<String>,
    /// The `host.id` of the host running this target
    pub active_host_id: Option<i32>,
    /// The list of `hosts.id`s the target can be mounted on
    /// taking HA configuration into account.
    pub host_ids: Vec<i32>,
    /// The list of `filesystem.name`s this target belongs to.
    /// Only an `MGS` may have more than one filesystem.
    pub filesystems: Vec<String>,
    /// Then underlying device UUID
    pub uuid: String,
    /// Where this target is mounted
    pub mount_path: Option<String>,
    /// The filesystem type associated with this target
    pub fs_type: Option<FsType>,
}

impl TargetRecord {
    pub fn get_kind(&self) -> TargetKind {
        get_kind(self.name.as_str())
    }
}

pub const TARGET_TABLE_NAME: TableName = TableName("target");

impl Id for TargetRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Id for &TargetRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for TargetRecord {
    fn label(&self) -> &str {
        &self.name
    }
}

impl Label for &TargetRecord {
    fn label(&self) -> &str {
        &self.name
    }
}

impl ToComponentType for TargetRecord {
    fn component_type(&self) -> ComponentType {
        ComponentType::Target
    }
}
