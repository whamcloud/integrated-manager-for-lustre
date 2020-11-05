// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::CompositeId;
use crate::ToCompositeId;
use crate::{EndpointName, Label};
use chrono::{offset::Utc, DateTime};
#[cfg(feature = "postgres-interop")]
use std::str::FromStr;
use std::{collections::BTreeSet, fmt, ops::Deref, path::PathBuf};

pub trait Id {
    /// Returns the `Id` (`i32`).
    fn id(&self) -> i32;
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

/// Record from the `django_content_type` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct ContentTypeRecord {
    pub id: i32,
    pub app_label: String,
    pub model: String,
}

impl Id for ContentTypeRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const CONTENT_TYPE_TABLE_NAME: TableName = TableName("django_content_type");

impl Name for ContentTypeRecord {
    fn table_name() -> TableName<'static> {
        CONTENT_TYPE_TABLE_NAME
    }
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

/// Record from the `chroma_core_managedfilesystem` table
#[derive(serde::Deserialize, Debug)]
pub struct FsRecord {
    id: i32,
    state_modified_at: String,
    state: String,
    immutable_state: bool,
    name: String,
    mgs_id: i32,
    mdt_next_index: i32,
    ost_next_index: i32,
    not_deleted: Option<bool>,
    content_type_id: Option<i32>,
}

impl Id for FsRecord {
    fn id(&self) -> i32 {
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
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct VolumeRecord {
    pub id: i32,
    pub storage_resource_id: Option<i32>,
    pub size: Option<i64>,
    pub label: String,
    pub filesystem_type: Option<String>,
    pub not_deleted: Option<bool>,
    pub usable_for_lustre: bool,
}

impl Id for VolumeRecord {
    fn id(&self) -> i32 {
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
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct VolumeNodeRecord {
    pub id: i32,
    pub volume_id: i32,
    pub host_id: i32,
    pub path: String,
    pub storage_resource_id: Option<i32>,
    pub primary: bool,
    pub r#use: bool,
    pub not_deleted: Option<bool>,
}

impl Id for VolumeNodeRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Id for &VolumeNodeRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl NotDeleted for VolumeNodeRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

impl Label for VolumeNodeRecord {
    fn label(&self) -> &str {
        &self.path
    }
}

impl Label for &VolumeNodeRecord {
    fn label(&self) -> &str {
        &self.path
    }
}

pub const VOLUME_NODE_TABLE_NAME: TableName = TableName("chroma_core_volumenode");

impl Name for VolumeNodeRecord {
    fn table_name() -> TableName<'static> {
        VOLUME_NODE_TABLE_NAME
    }
}

/// Record from the `chroma_core_managedtargetmount` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct ManagedTargetMountRecord {
    pub id: i32,
    pub host_id: i32,
    pub mount_point: Option<String>,
    pub volume_node_id: i32,
    pub primary: bool,
    pub target_id: i32,
    pub not_deleted: Option<bool>,
}

impl Id for ManagedTargetMountRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl NotDeleted for ManagedTargetMountRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
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
    id: i32,
    state_modified_at: String,
    state: String,
    immutable_state: bool,
    name: Option<String>,
    uuid: Option<String>,
    ha_label: Option<String>,
    volume_id: i32,
    inode_size: Option<i32>,
    bytes_per_inode: Option<i32>,
    inode_count: Option<u64>,
    reformat: bool,
    active_mount_id: Option<i32>,
    not_deleted: Option<bool>,
    content_type_id: Option<i32>,
}

impl Id for ManagedTargetRecord {
    fn id(&self) -> i32 {
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

/// Record from the `chroma_core_ostpool` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct OstPoolRecord {
    pub id: i32,
    pub name: String,
    pub filesystem_id: i32,
    pub not_deleted: Option<bool>,
    pub content_type_id: Option<i32>,
}

impl Id for OstPoolRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Id for &OstPoolRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl NotDeleted for OstPoolRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

pub const OSTPOOL_TABLE_NAME: TableName = TableName("chroma_core_ostpool");

impl Name for OstPoolRecord {
    fn table_name() -> TableName<'static> {
        OSTPOOL_TABLE_NAME
    }
}

impl Label for OstPoolRecord {
    fn label(&self) -> &str {
        &self.name
    }
}

impl Label for &OstPoolRecord {
    fn label(&self) -> &str {
        &self.name
    }
}

/// Record from the `chroma_core_ostpool_osts` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct OstPoolOstsRecord {
    pub id: i32,
    pub ostpool_id: i32,
    pub managedost_id: i32,
}

impl Id for OstPoolOstsRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const OSTPOOL_OSTS_TABLE_NAME: TableName = TableName("chroma_core_ostpool_osts");

impl Name for OstPoolOstsRecord {
    fn table_name() -> TableName<'static> {
        OSTPOOL_OSTS_TABLE_NAME
    }
}

/// Record from the `chroma_core_managedost` table
#[derive(serde::Deserialize, Debug)]
pub struct ManagedOstRecord {
    managedtarget_ptr_id: i32,
    index: i32,
    filesystem_id: i32,
}

impl Id for ManagedOstRecord {
    fn id(&self) -> i32 {
        self.managedtarget_ptr_id
    }
}

impl NotDeleted for ManagedOstRecord {
    fn not_deleted(&self) -> bool {
        true
    }
}

pub const MANAGED_OST_TABLE_NAME: TableName = TableName("chroma_core_managedost");

impl Name for ManagedOstRecord {
    fn table_name() -> TableName<'static> {
        MANAGED_OST_TABLE_NAME
    }
}

/// Record from the `chroma_core_managedmdt` table
#[derive(serde::Deserialize, Debug)]
pub struct ManagedMdtRecord {
    managedtarget_ptr_id: i32,
    index: i32,
    filesystem_id: i32,
}

impl Id for ManagedMdtRecord {
    fn id(&self) -> i32 {
        self.managedtarget_ptr_id
    }
}

impl NotDeleted for ManagedMdtRecord {
    fn not_deleted(&self) -> bool {
        true
    }
}

pub const MANAGED_MDT_TABLE_NAME: TableName = TableName("chroma_core_managedmdt");

impl Name for ManagedMdtRecord {
    fn table_name() -> TableName<'static> {
        MANAGED_MDT_TABLE_NAME
    }
}

/// Record from the `chroma_core_managedhost` table
#[derive(serde::Deserialize, Debug)]
pub struct ManagedHostRecord {
    pub id: i32,
    pub state_modified_at: DateTime<Utc>,
    pub state: String,
    pub immutable_state: bool,
    pub not_deleted: Option<bool>,
    pub content_type_id: Option<i32>,
    pub address: String,
    pub fqdn: String,
    pub nodename: String,
    pub boot_time: Option<DateTime<Utc>>,
    pub server_profile_id: Option<String>,
    pub needs_update: bool,
    pub install_method: String,
    pub corosync_ring0: String,
}

impl Id for ManagedHostRecord {
    fn id(&self) -> i32 {
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

impl ManagedHostRecord {
    pub fn is_setup(&self) -> bool {
        ["monitored", "managed", "working"]
            .iter()
            .any(|&x| x == self.state)
    }
}

/// Record from the `chroma_core_alertstate` table
#[derive(serde::Deserialize, Debug)]
pub struct AlertStateRecord {
    id: i32,
    alert_item_type_id: Option<i32>,
    alert_item_id: Option<i32>,
    alert_type: String,
    begin: String,
    end: Option<String>,
    active: Option<bool>,
    dismissed: bool,
    severity: i32,
    record_type: String,
    variant: Option<String>,
    lustre_pid: Option<i32>,
    message: Option<String>,
}

impl AlertStateRecord {
    pub fn is_active(&self) -> bool {
        self.active.is_some()
    }
}

impl Id for AlertStateRecord {
    fn id(&self) -> i32 {
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
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct StratagemConfiguration {
    pub id: i32,
    pub filesystem_id: i32,
    pub interval: i64,
    pub report_duration: Option<i64>,
    pub purge_duration: Option<i64>,
    pub immutable_state: bool,
    pub not_deleted: Option<bool>,
    pub state: String,
    pub state_modified_at: DateTime<Utc>,
}

impl Id for StratagemConfiguration {
    fn id(&self) -> i32 {
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

impl Label for StratagemConfiguration {
    fn label(&self) -> &str {
        "Stratagem Configuration"
    }
}

impl EndpointName for StratagemConfiguration {
    fn endpoint_name() -> &'static str {
        "stratagem_configuration"
    }
}

/// Record from the `chroma_core_lnetconfiguration` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct LnetConfigurationRecord {
    pub id: i32,
    pub state: String,
    pub host_id: i32,
    pub immutable_state: bool,
    pub not_deleted: Option<bool>,
    pub content_type_id: Option<i32>,
    pub state_modified_at: DateTime<Utc>,
}

impl Id for LnetConfigurationRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl NotDeleted for LnetConfigurationRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

impl EndpointName for LnetConfigurationRecord {
    fn endpoint_name() -> &'static str {
        "lnet_configuration"
    }
}

impl Label for LnetConfigurationRecord {
    fn label(&self) -> &str {
        "lnet configuration"
    }
}

impl ToCompositeId for LnetConfigurationRecord {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id.unwrap(), self.id)
    }
}

impl ToCompositeId for &LnetConfigurationRecord {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id.unwrap(), self.id)
    }
}

pub const LNET_CONFIGURATION_TABLE_NAME: TableName = TableName("chroma_core_lnetconfiguration");

impl Name for LnetConfigurationRecord {
    fn table_name() -> TableName<'static> {
        LNET_CONFIGURATION_TABLE_NAME
    }
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
    Zpool,
    Dataset,
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
            Self::Zpool => write!(f, "zpool"),
            Self::Dataset => write!(f, "dataset"),
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

/// Record from the `chroma_core_pacemakerconfiguration` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct PacemakerConfigurationRecord {
    pub id: i32,
    pub state: String,
    pub state_modified_at: DateTime<Utc>,
    pub immutable_state: bool,
    pub not_deleted: Option<bool>,
    pub content_type_id: Option<i32>,
    pub host_id: i32,
}

pub const PACEMAKER_CONFIGURATION_TABLE_NAME: TableName =
    TableName("chroma_core_pacemakerconfiguration");

impl Name for PacemakerConfigurationRecord {
    fn table_name() -> TableName<'static> {
        PACEMAKER_CONFIGURATION_TABLE_NAME
    }
}

impl Id for PacemakerConfigurationRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl NotDeleted for PacemakerConfigurationRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

impl EndpointName for PacemakerConfigurationRecord {
    fn endpoint_name() -> &'static str {
        "pacemaker_configuration"
    }
}

impl Label for PacemakerConfigurationRecord {
    fn label(&self) -> &str {
        "pacemaker configuration"
    }
}

impl ToCompositeId for PacemakerConfigurationRecord {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id.unwrap(), self.id)
    }
}

impl ToCompositeId for &PacemakerConfigurationRecord {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id.unwrap(), self.id)
    }
}

/// Record from the `chroma_core_corosyncconfiguration` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct CorosyncConfigurationRecord {
    pub id: i32,
    pub state: String,
    pub state_modified_at: DateTime<Utc>,
    pub immutable_state: bool,
    pub not_deleted: Option<bool>,
    pub mcast_port: Option<i32>,
    pub corosync_reported_up: bool,
    pub content_type_id: Option<i32>,
    pub host_id: i32,
    pub record_type: String,
}

pub const COROSYNC_CONFIGURATION_TABLE_NAME: TableName =
    TableName("chroma_core_corosyncconfiguration");

impl Name for CorosyncConfigurationRecord {
    fn table_name() -> TableName<'static> {
        COROSYNC_CONFIGURATION_TABLE_NAME
    }
}

impl Id for CorosyncConfigurationRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl NotDeleted for CorosyncConfigurationRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

impl EndpointName for CorosyncConfigurationRecord {
    fn endpoint_name() -> &'static str {
        "corosync_configuration"
    }
}

impl Label for CorosyncConfigurationRecord {
    fn label(&self) -> &str {
        "corosync configuration"
    }
}

impl ToCompositeId for CorosyncConfigurationRecord {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id.unwrap(), self.id)
    }
}

impl ToCompositeId for &CorosyncConfigurationRecord {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id.unwrap(), self.id)
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

/// Record from `chroma_core_serverprofile` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct ServerProfileRecord {
    pub corosync: bool,
    pub corosync2: bool,
    pub default: bool,
    pub initial_state: String,
    pub managed: bool,
    pub name: String,
    pub ntp: bool,
    pub pacemaker: bool,
    pub ui_description: String,
    pub ui_name: String,
    pub user_selectable: bool,
    pub worker: bool,
}

pub const SERVER_PROFILE_TABLE_NAME: TableName = TableName("chroma_core_serverprofile");

impl Name for ServerProfileRecord {
    fn table_name() -> TableName<'static> {
        SERVER_PROFILE_TABLE_NAME
    }
}
