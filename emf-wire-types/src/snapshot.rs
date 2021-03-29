// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Data structures for communicating with the agent regarding lustre snapshots.

use crate::{
    db::{Id, TableName},
    duration::GraphQLDuration,
};
use chrono::{offset::Utc, DateTime};
use std::str::FromStr;
#[cfg(feature = "cli")]
use structopt::StructOpt;

#[derive(serde::Deserialize, serde::Serialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to list snapshots
pub struct List {
    /// Target name
    pub target: String,
    /// Name of the snapshot to list
    pub name: Option<String>,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
/// Snapshots description
pub struct Snapshot {
    pub filesystem_name: String,
    pub snapshot_name: String,
    /// Snapshot filesystem id (random string)
    pub snapshot_fsname: String,
    pub modify_time: DateTime<Utc>,
    pub create_time: DateTime<Utc>,
    pub mounted: bool,
    /// Optional comment for the snapshot
    pub comment: Option<String>,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
pub struct SnapshotRecord {
    pub id: i32,
    pub filesystem_name: String,
    pub snapshot_name: String,
    pub modify_time: DateTime<Utc>,
    pub create_time: DateTime<Utc>,
    pub snapshot_fsname: String,
    pub mounted: bool,
    pub comment: Option<String>,
}

impl Id for SnapshotRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const SNAPSHOT_TABLE_NAME: TableName = TableName("snapshot");

#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
/// A Snapshot interval
pub struct SnapshotInterval {
    /// The configuration id
    pub id: i32,
    /// The filesystem name
    pub filesystem_name: String,
    /// Use a write barrier
    pub use_barrier: bool,
    /// The interval configuration
    pub interval: GraphQLDuration,
    // Last known run
    pub last_run: Option<DateTime<Utc>>,
}

impl Id for SnapshotInterval {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const SNAPSHOT_INTERVAL_TABLE_NAME: TableName = TableName("snapshot_interval");

#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
pub struct SnapshotRetention {
    pub id: i32,
    pub filesystem_name: String,
    /// Amount or percent of free space to reserve
    pub reserve_value: i32,
    pub reserve_unit: ReserveUnit,
    /// Minimum number of snapshots to keep
    pub keep_num: i32,
    pub last_run: Option<DateTime<Utc>>,
}

impl Id for SnapshotRetention {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const SNAPSHOT_RETENTION_TABLE_NAME: TableName = TableName("snapshot_retention");

#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(
    feature = "postgres-interop",
    sqlx(type_name = "snapshot_reserve_unit")
)]
#[cfg_attr(feature = "postgres-interop", sqlx(rename_all = "lowercase"))]
#[derive(serde::Deserialize, serde::Serialize, Clone, Copy, PartialEq, Debug)]
#[serde(rename_all = "lowercase")]
pub enum ReserveUnit {
    #[cfg_attr(feature = "graphql", graphql(name = "percent"))]
    Percent,
    #[cfg_attr(feature = "graphql", graphql(name = "gibibytes"))]
    Gibibytes,
    #[cfg_attr(feature = "graphql", graphql(name = "tebibytes"))]
    Tebibytes,
}

impl FromStr for ReserveUnit {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "%" | "percent" => Ok(Self::Percent),
            "gib" | "g" | "gibibytes" => Ok(Self::Gibibytes),
            "tib" | "t" | "tebibytes" => Ok(Self::Tebibytes),
            x => Err(format!("Unexpected '{}'", x)),
        }
    }
}

#[derive(serde::Deserialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to create a snapshot
pub struct Create {
    /// Filesystem name
    pub fsname: String,
    /// Snapshot name
    pub name: String,
    /// Set write barrier before creating snapshot
    #[cfg_attr(feature = "cli", structopt(short = "b", long = "use_barrier"))]
    pub use_barrier: bool,
    /// Optional comment for the snapshot
    #[cfg_attr(feature = "cli", structopt(short = "c", long = "comment"))]
    pub comment: Option<String>,
}

#[derive(serde::Deserialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to destroy the snapshot
pub struct Destroy {
    /// Filesystem name
    pub fsname: String,
    /// Name of the snapshot to destroy
    pub name: String,

    /// Destroy the snapshot by force
    #[cfg_attr(feature = "cli", structopt(short = "f", long = "force"))]
    pub force: bool,
}

#[derive(serde::Deserialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to mount the snapshot
pub struct Mount {
    /// Filesystem name
    pub fsname: String,
    /// Snapshot name
    pub name: String,
}

#[derive(serde::Deserialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to unmount the snapshot
pub struct Unmount {
    /// Filesystem name
    pub fsname: String,
    /// Name of the snapshot
    pub name: String,
}
