// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Data structures for communicating with the agent regarding lustre snapshots.

use crate::{
    db::{Id, TableName},
    graphql_duration::GraphQLDuration,
};
use chrono::{offset::Utc, DateTime};
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
#[derive(serde::Deserialize, serde::Serialize, Eq, Clone, Debug)]
/// Automatic snapshot policy
pub struct SnapshotPolicy {
    /// The configuration id
    pub id: i32,
    /// The filesystem name
    pub filesystem: String,
    /// The interval configuration
    pub interval: GraphQLDuration,
    /// Preferred time to start creating automatic snapshots at
    pub start: Option<DateTime<Utc>>,
    /// Use a write barrier
    pub barrier: bool,
    /// Number of recent snapshots to keep
    pub keep: i32,
    /// The number of days when keep the most recent snapshot of each day
    pub daily: i32,
    /// The number of weeks when keep the most recent snapshot of each week
    pub weekly: i32,
    /// The number of months when keep the most recent snapshot of each month
    pub monthly: i32,
    /// Last known run
    pub last_run: Option<DateTime<Utc>>,
}

impl PartialEq for SnapshotPolicy {
    fn eq(&self, other: &Self) -> bool {
        self.filesystem == other.filesystem
            && self.interval == other.interval
            && self.start == other.start
            && self.barrier == other.barrier
            && self.keep == other.keep
            && self.daily == other.daily
            && self.weekly == other.weekly
            && self.monthly == other.monthly
    }
}

impl std::hash::Hash for SnapshotPolicy {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.filesystem.hash(state);
        self.interval.hash(state);
        self.start.hash(state);
        self.barrier.hash(state);
        self.keep.hash(state);
        self.daily.hash(state);
        self.weekly.hash(state);
        self.monthly.hash(state);
    }
}

impl Id for SnapshotPolicy {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const SNAPSHOT_POLICY_TABLE_NAME: TableName = TableName("snapshot_policy");

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
