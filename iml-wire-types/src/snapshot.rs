// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Data structures for communicating with the agent regarding lustre snapshots.

use chrono::offset::Utc;
use chrono::DateTime;
#[cfg(feature = "cli")]
use structopt::StructOpt;

#[derive(serde::Deserialize, serde::Serialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to list snapshots
pub struct List {
    /// Filesystem name
    pub fsname: String,
    /// Name of the snapshot to list
    pub name: Option<String>,

    /// List details
    #[cfg_attr(feature = "cli", structopt(short = "d", long = "detail"))]
    pub detail: bool,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
/// Snapshots description
pub struct Snapshot {
    pub filesystem_name: String,
    pub snapshot_name: String,
    /// Snapshot members
    pub details: Vec<Detail>,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
pub enum Status {
    Mounted,
    NotMounted,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct Detail {
    /// E. g. MDT0000
    pub snapshot_role: Option<String>,
    /// Filesystem id (random string)
    pub snapshot_fsname: String,
    pub modify_time: DateTime<Utc>,
    pub create_time: DateTime<Utc>,
    /// Snapshot status (None means unknown)
    pub status: Option<Status>,
    /// Optional comment for the snapshot
    pub comment: Option<String>,
}

#[derive(serde::Deserialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to create a snapshot
pub struct Create {
    /// Filesystem name
    pub fsname: String,
    /// Snapshot name
    pub name: String,

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
