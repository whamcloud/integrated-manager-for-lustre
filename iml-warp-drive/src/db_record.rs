// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_postgres::Row;
use serde::de::Error;
use std::{convert::TryFrom, fmt};

pub trait Id {
    /// Returns the `Id` (`u32`).
    fn id(&self) -> u32;
}

pub trait NotDeleted {
    /// Returns if the record is not deleted.
    fn not_deleted(&self) -> bool;
    /// Returns if the record is deleted.
    fn deleted(&self) -> bool {
        !self.not_deleted()
    }
}

fn not_deleted(x: Option<bool>) -> bool {
    x.filter(|&x| x).is_some()
}

/// The name of a `chroma` table
#[derive(serde::Deserialize, Debug, PartialEq, Eq)]
#[serde(transparent)]
pub struct TableName<'a>(&'a str);

impl fmt::Display for TableName<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

pub trait Name {
    /// Get the name of a `chroma` table
    fn table_name() -> TableName<'static>;
}

/// Record from the `chroma_core_managedfilesystem` table
#[derive(serde::Deserialize, Debug)]
pub struct FsRecord {
    id: u32,
    state_modified_at: String,
    state: String,
    immutable_state: bool,
    name: String,
    mgs_id: u32,
    mdt_next_index: u32,
    ost_next_index: u32,
    not_deleted: Option<bool>,
    content_type_id: Option<u32>,
}

impl Id for FsRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for FsRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const MANAGED_FILESYSTEM_TABLE_NAME: TableName = TableName("chroma_core_managedfilesystem");

impl Name for FsRecord {
    fn table_name() -> TableName<'static> {
        MANAGED_FILESYSTEM_TABLE_NAME
    }
}

/// Record from the `chroma_core_volume` table
#[derive(serde::Deserialize, Debug)]
pub struct VolumeRecord {
    id: u32,
    storage_resource_id: Option<u32>,
    size: Option<u64>,
    label: String,
    filesystem_type: Option<String>,
    not_deleted: Option<bool>,
    usable_for_lustre: bool,
}

impl Id for VolumeRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for VolumeRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const VOLUME_TABLE_NAME: TableName = TableName("chroma_core_volume");

impl Name for VolumeRecord {
    fn table_name() -> TableName<'static> {
        VOLUME_TABLE_NAME
    }
}

/// Record from the `chroma_core_volumenode` table
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct VolumeNodeRecord {
    id: u32,
    volume_id: u32,
    host_id: u32,
    path: String,
    storage_resource_id: Option<u32>,
    primary: bool,
    #[serde(rename = "use")]
    _use: bool,
    not_deleted: Option<bool>,
}

impl Id for VolumeNodeRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for VolumeNodeRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const VOLUME_NODE_TABLE_NAME: TableName = TableName("chroma_core_volumenode");

impl Name for VolumeNodeRecord {
    fn table_name() -> TableName<'static> {
        VOLUME_NODE_TABLE_NAME
    }
}

impl From<Row> for VolumeNodeRecord {
    fn from(row: Row) -> Self {
        VolumeNodeRecord {
            id: row.get::<_, i32>("id") as u32,
            volume_id: row.get::<_, i32>("volume_id") as u32,
            host_id: row.get::<_, i32>("host_id") as u32,
            path: row.get("path"),
            storage_resource_id: row
                .get::<_, Option<i32>>("storage_resource_id")
                .map(|x| x as u32),
            primary: row.get("primary"),
            _use: row.get("use"),
            not_deleted: row.get("not_deleted"),
        }
    }
}

/// Record from the `chroma_core_managedtargetmount` table
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct ManagedTargetMountRecord {
    id: u32,
    host_id: u32,
    mount_point: Option<String>,
    volume_node_id: u32,
    primary: bool,
    target_id: u32,
    not_deleted: Option<bool>,
}

impl Id for ManagedTargetMountRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for ManagedTargetMountRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

impl From<Row> for ManagedTargetMountRecord {
    fn from(row: Row) -> Self {
        ManagedTargetMountRecord {
            id: row.get::<_, i32>("id") as u32,
            host_id: row.get::<_, i32>("host_id") as u32,
            mount_point: row.get("mount_point"),
            volume_node_id: row.get::<_, i32>("volume_node_id") as u32,
            primary: row.get("primary"),
            target_id: row.get::<_, i32>("target_id") as u32,
            not_deleted: row.get("not_deleted"),
        }
    }
}

pub const MANAGED_TARGET_MOUNT_TABLE_NAME: TableName = TableName("chroma_core_managedtargetmount");

impl Name for ManagedTargetMountRecord {
    fn table_name() -> TableName<'static> {
        MANAGED_TARGET_MOUNT_TABLE_NAME
    }
}

/// Record from the `chroma_core_managedtarget` table
#[derive(serde::Deserialize, Debug)]
pub struct ManagedTargetRecord {
    id: u32,
    state_modified_at: String,
    state: String,
    immutable_state: bool,
    name: Option<String>,
    uuid: Option<String>,
    ha_label: Option<String>,
    volume_id: u32,
    inode_size: Option<u32>,
    bytes_per_inode: Option<u32>,
    inode_count: Option<u64>,
    reformat: bool,
    active_mount_id: Option<u32>,
    not_deleted: Option<bool>,
    content_type_id: Option<u32>,
}

impl Id for ManagedTargetRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for ManagedTargetRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const MANAGED_TARGET_TABLE_NAME: TableName = TableName("chroma_core_managedtarget");

impl Name for ManagedTargetRecord {
    fn table_name() -> TableName<'static> {
        MANAGED_TARGET_TABLE_NAME
    }
}

/// Record from the `chroma_core_managedhost` table
#[derive(serde::Deserialize, Debug)]
pub struct ManagedHostRecord {
    id: u32,
    state_modified_at: String,
    state: String,
    immutable_state: bool,
    not_deleted: Option<bool>,
    content_type_id: Option<u32>,
    address: String,
    fqdn: String,
    nodename: String,
    boot_time: Option<String>,
    server_profile_id: Option<String>,
    needs_update: bool,
    install_method: String,
    properties: String,
    corosync_ring0: String,
}

impl Id for ManagedHostRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for ManagedHostRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const MANAGED_HOST_TABLE_NAME: TableName = TableName("chroma_core_managedhost");

impl Name for ManagedHostRecord {
    fn table_name() -> TableName<'static> {
        MANAGED_HOST_TABLE_NAME
    }
}

/// Record from the `chroma_core_alertstate` table
#[derive(serde::Deserialize, Debug)]
pub struct AlertStateRecord {
    id: u32,
    alert_item_type_id: Option<u32>,
    alert_item_id: Option<u32>,
    alert_type: String,
    begin: String,
    end: Option<String>,
    active: Option<bool>,
    dismissed: bool,
    severity: u32,
    record_type: String,
    variant: Option<String>,
    lustre_pid: Option<u32>,
    message: Option<String>,
}

impl AlertStateRecord {
    pub fn is_active(&self) -> bool {
        self.active.is_some()
    }
}

impl Id for AlertStateRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

pub const ALERT_STATE_TABLE_NAME: TableName = TableName("chroma_core_alertstate");

impl Name for AlertStateRecord {
    fn table_name() -> TableName<'static> {
        ALERT_STATE_TABLE_NAME
    }
}

/// Record from the `chroma_core_stratagemconfiguration` table
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct StratagemConfiguration {
    pub id: u32,
    pub filesystem_id: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
    pub immutable_state: bool,
    pub not_deleted: Option<bool>,
    pub state: String,
}

impl From<Row> for StratagemConfiguration {
    fn from(row: Row) -> Self {
        StratagemConfiguration {
            id: row.get::<_, i32>("id") as u32,
            filesystem_id: row.get::<_, i32>("filesystem_id") as u32,
            interval: row.get::<_, i64>("interval") as u64,
            report_duration: row
                .get::<_, Option<i64>>("report_duration")
                .map(|x| x as u64),
            purge_duration: row
                .get::<_, Option<i64>>("purge_duration")
                .map(|x| x as u64),
            immutable_state: row.get("immutable_state"),
            not_deleted: row.get("not_deleted"),
            state: row.get("state"),
        }
    }
}

impl Id for StratagemConfiguration {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for StratagemConfiguration {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const STRATAGEM_CONFIGURATION_TABLE_NAME: TableName =
    TableName("chroma_core_stratagemconfiguration");

impl Name for StratagemConfiguration {
    fn table_name() -> TableName<'static> {
        STRATAGEM_CONFIGURATION_TABLE_NAME
    }
}

/// Record from the `chroma_core_lnetconfiguration` table
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct LnetConfigurationRecord {
    id: u32,
    state: String,
    host_id: u32,
    immutable_state: bool,
    not_deleted: Option<bool>,
    content_type_id: Option<u32>,
}

impl From<Row> for LnetConfigurationRecord {
    fn from(row: Row) -> Self {
        LnetConfigurationRecord {
            id: row.get::<_, i32>("id") as u32,
            state: row.get("state"),
            host_id: row.get::<_, i32>("host_id") as u32,
            immutable_state: row.get("immutable_state"),
            not_deleted: row.get("not_deleted"),
            content_type_id: row
                .get::<_, Option<i32>>("content_type_id")
                .map(|x| x as u32),
        }
    }
}

impl Id for LnetConfigurationRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for LnetConfigurationRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const LNET_CONFIGURATION_TABLE_NAME: TableName = TableName("chroma_core_lnetconfiguration");

impl Name for LnetConfigurationRecord {
    fn table_name() -> TableName<'static> {
        LNET_CONFIGURATION_TABLE_NAME
    }
}

/// Records from `chroma` database.
#[derive(Debug)]
pub enum DbRecord {
    ManagedFilesystem(FsRecord),
    ManagedTargetMount(ManagedTargetMountRecord),
    ManagedTarget(ManagedTargetRecord),
    ManagedHost(ManagedHostRecord),
    Volume(VolumeRecord),
    VolumeNode(VolumeNodeRecord),
    AlertState(AlertStateRecord),
    StratagemConfiguration(StratagemConfiguration),
    LnetConfiguration(LnetConfigurationRecord),
}

impl TryFrom<(TableName<'_>, serde_json::Value)> for DbRecord {
    type Error = serde_json::Error;

    /// Performs the conversion. It would be simpler to deserialize from an untagged representation,
    /// but need to check the perf characteristics of it.
    fn try_from((table_name, x): (TableName, serde_json::Value)) -> Result<Self, Self::Error> {
        match table_name {
            MANAGED_FILESYSTEM_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::ManagedFilesystem)
            }
            VOLUME_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Volume),
            VOLUME_NODE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::VolumeNode),
            MANAGED_TARGET_MOUNT_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::ManagedTargetMount)
            }
            MANAGED_TARGET_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedTarget),
            MANAGED_HOST_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedHost),
            ALERT_STATE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AlertState),
            STRATAGEM_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::StratagemConfiguration)
            }
            LNET_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::LnetConfiguration)
            }
            x => Err(serde_json::Error::custom(format!(
                "No matching table representation for {}",
                x
            ))),
        }
    }
}
