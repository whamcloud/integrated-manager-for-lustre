// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::{offset::Utc, DateTime};
#[cfg(feature = "postgres-interop")]
use std::str::FromStr;
use std::{collections::BTreeSet, fmt, ops::Deref, path::PathBuf};

pub trait Id {
    /// Returns the `Id` (`i32`).
    fn id(&self) -> i32;
}

/// The name of a `chroma` table
#[derive(serde::Deserialize, Debug, PartialEq, Eq)]
#[serde(transparent)]
pub struct TableName<'a>(pub &'a str);

impl fmt::Display for TableName<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

pub trait Name {
    /// Get the name of a `chroma` table
    fn table_name() -> TableName<'static>;
}

/// Record from the `lustre_fid` type
#[cfg(feature = "postgres-interop")]
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug, sqlx::Type)]
#[sqlx(rename = "lustre_fid")]
pub struct LustreFid {
    pub seq: i64,
    pub oid: i32,
    pub ver: i32,
}

#[cfg(feature = "postgres-interop")]
impl fmt::Display for LustreFid {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "[0x{:x}:0x{:x}:0x{:x}]",
            self.seq as u64, self.oid as u32, self.ver as u32
        )
    }
}

#[cfg(feature = "postgres-interop")]
impl FromStr for LustreFid {
    type Err = std::num::ParseIntError;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let fidstr = s.trim_matches(|c| c == '[' || c == ']');
        let arr: Vec<&str> = fidstr
            .split(':')
            .map(|num| num.trim_start_matches("0x"))
            .collect();
        Ok(Self {
            seq: i64::from_str_radix(arr[0], 16)?,
            oid: i32::from_str_radix(arr[1], 16)?,
            ver: i32::from_str_radix(arr[2], 16)?,
        })
    }
}

/// Record from the `chroma_core_fidtaskqueue` table
#[cfg(feature = "postgres-interop")]
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct FidTaskQueue {
    pub id: i32,
    pub fid: LustreFid,
    pub data: serde_json::Value,
    pub task_id: i32,
}

#[derive(
    Debug, serde::Serialize, serde::Deserialize, Eq, PartialEq, Ord, PartialOrd, Clone, Hash,
)]
pub struct DeviceId(String);

impl Deref for DeviceId {
    type Target = String;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct DeviceIds(pub BTreeSet<DeviceId>);

impl Deref for DeviceIds {
    type Target = BTreeSet<DeviceId>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

#[derive(Debug, PartialEq, Eq)]
pub struct Size(pub u64);

/// The current type of Devices we support
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize)]
pub enum DeviceType {
    ScsiDevice,
    Partition,
    MdRaid,
    Mpath,
    VolumeGroup,
    LogicalVolume,
}

impl std::fmt::Display for DeviceType {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::ScsiDevice => write!(f, "scsi"),
            Self::Partition => write!(f, "partition"),
            Self::MdRaid => write!(f, "mdraid"),
            Self::Mpath => write!(f, "mpath"),
            Self::VolumeGroup => write!(f, "vg"),
            Self::LogicalVolume => write!(f, "lv"),
        }
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct Command {
    pub id: i32,
    pub complete: bool,
    pub errored: bool,
    pub cancelled: bool,
    pub message: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, PartialEq, Eq)]
pub struct Paths(pub BTreeSet<PathBuf>);

impl Deref for Paths {
    type Target = BTreeSet<PathBuf>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

#[derive(Debug, PartialEq, Eq)]
pub struct MountPath(pub Option<PathBuf>);

#[cfg(feature = "postgres-interop")]
impl Deref for MountPath {
    type Target = Option<PathBuf>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

/// Record from the `auth_user` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct AuthUserRecord {
    pub id: i32,
    pub is_superuser: bool,
    pub username: String,
    pub first_name: String,
    pub last_name: String,
    pub email: String,
    pub is_staff: bool,
    pub is_active: bool,
}

pub const AUTH_USER_TABLE_NAME: TableName = TableName("auth_user");

impl Name for AuthUserRecord {
    fn table_name() -> TableName<'static> {
        AUTH_USER_TABLE_NAME
    }
}

impl Id for AuthUserRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

/// Record from the `auth_user_groups` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct AuthUserGroupRecord {
    pub id: i32,
    pub user_id: i32,
    pub group_id: i32,
}

pub const AUTH_USER_GROUP_TABLE_NAME: TableName = TableName("auth_user_groups");

impl Name for AuthUserGroupRecord {
    fn table_name() -> TableName<'static> {
        AUTH_USER_GROUP_TABLE_NAME
    }
}

impl Id for AuthUserGroupRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

/// Record from the `auth_group` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct AuthGroupRecord {
    pub id: i32,
    pub name: String,
}

pub const AUTH_GROUP_TABLE_NAME: TableName = TableName("auth_group");

impl Name for AuthGroupRecord {
    fn table_name() -> TableName<'static> {
        AUTH_GROUP_TABLE_NAME
    }
}

impl Id for AuthGroupRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

/// Record from the `chroma_core_logmessage` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct LogMessageRecord {
    pub id: i32,
    pub datetime: chrono::DateTime<Utc>,
    pub fqdn: String,
    pub severity: i16,
    pub facility: i16,
    pub tag: String,
    pub message: String,
    pub message_class: i16,
}

pub const LOG_MESSAGE_TABLE_NAME: TableName = TableName("chroma_core_logmessage");

impl Name for LogMessageRecord {
    fn table_name() -> TableName<'static> {
        LOG_MESSAGE_TABLE_NAME
    }
}

impl Id for LogMessageRecord {
    fn id(&self) -> i32 {
        self.id
    }
}
