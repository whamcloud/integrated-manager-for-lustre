// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{Id, TableName},
    Label,
};

/// Record from the corosync_resource table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct CorosyncResourceRecord {
    pub id: i32,
    pub name: String,
    pub cluster_id: i32,
    pub resource_agent: String,
    pub role: String,
    pub active: bool,
    pub orphaned: bool,
    pub managed: bool,
    pub failed: bool,
    pub failure_ignored: bool,
    pub nodes_running_on: i32,
    pub active_node_id: Option<String>,
    pub active_node_name: Option<String>,
    pub mount_point: Option<String>,
}

impl Id for CorosyncResourceRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for CorosyncResourceRecord {
    fn label(&self) -> &str {
        "corosync resource"
    }
}

pub const COROSYNC_RESOURCE_TABLE_NAME: TableName = TableName("corosync_resource");

/// Record from the corosync_resource_bans table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct CorosyncResourceBanRecord {
    pub id: i32,
    pub name: String,
    pub cluster_id: i32,
    pub resource: String,
    pub node: String,
    pub weight: i32,
    pub master_only: bool,
}

pub const COROSYNC_RESOURCE_BAN_TABLE_NAME: TableName = TableName("corosync_resource_bans");

impl Id for CorosyncResourceBanRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for CorosyncResourceBanRecord {
    fn label(&self) -> &str {
        "corosync resource ban"
    }
}
