use crate::{Fqdn, Label};
use std::{collections::BTreeSet, fmt, ops::{Deref, DerefMut}, path::PathBuf};

#[cfg(feature = "postgres-interop")]
use bytes::BytesMut;
#[cfg(feature = "postgres-interop")]
use postgres_types::{to_sql_checked, FromSql, IsNull, ToSql, Type};
#[cfg(feature = "postgres-interop")]
use std::io;
#[cfg(feature = "postgres-interop")]
use tokio_postgres::Row;

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
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct VolumeNodeRecord {
    pub id: u32,
    pub volume_id: u32,
    pub host_id: u32,
    pub path: String,
    pub storage_resource_id: Option<u32>,
    pub primary: bool,
    #[serde(rename = "use")]
    pub _use: bool,
    pub not_deleted: Option<bool>,
}

impl Id for VolumeNodeRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl Id for &VolumeNodeRecord {
    fn id(&self) -> u32 {
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

#[cfg(feature = "postgres-interop")]
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
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct ManagedTargetMountRecord {
    pub id: u32,
    pub host_id: u32,
    pub mount_point: Option<String>,
    pub volume_node_id: u32,
    pub primary: bool,
    pub target_id: u32,
    pub not_deleted: Option<bool>,
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

#[cfg(feature = "postgres-interop")]
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

/// Record from the `chroma_core_ostpool` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct OstPoolRecord {
    pub id: u32,
    pub name: String,
    pub filesystem_id: u32,
    pub not_deleted: Option<bool>,
    pub content_type_id: Option<u32>,
}

impl Id for OstPoolRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl Id for &OstPoolRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

impl NotDeleted for OstPoolRecord {
    fn not_deleted(&self) -> bool {
        not_deleted(self.not_deleted)
    }
}

#[cfg(feature = "postgres-interop")]
impl From<Row> for OstPoolRecord {
    fn from(row: Row) -> Self {
        OstPoolRecord {
            id: row.get::<_, i32>("id") as u32,
            name: row.get("name"),
            filesystem_id: row.get::<_, i32>("filesystem_id") as u32,
            not_deleted: row.get("not_deleted"),
            content_type_id: row
                .get::<_, Option<i32>>("content_type_id")
                .map(|x| x as u32),
        }
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
    pub id: u32,
    pub ostpool_id: u32,
    pub managedost_id: u32,
}

impl Id for OstPoolOstsRecord {
    fn id(&self) -> u32 {
        self.id
    }
}

#[cfg(feature = "postgres-interop")]
impl From<Row> for OstPoolOstsRecord {
    fn from(row: Row) -> Self {
        OstPoolOstsRecord {
            id: row.get::<_, i32>("id") as u32,
            ostpool_id: row.get::<_, i32>("ostpool_id") as u32,
            managedost_id: row.get::<_, i32>("managedost_id") as u32,
        }
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
    managedtarget_ptr_id: u32,
    index: u32,
    filesystem_id: u32,
}

impl Id for ManagedOstRecord {
    fn id(&self) -> u32 {
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
    managedtarget_ptr_id: u32,
    index: u32,
    filesystem_id: u32,
}

impl Id for ManagedMdtRecord {
    fn id(&self) -> u32 {
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
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
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

#[cfg(feature = "postgres-interop")]
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
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct LnetConfigurationRecord {
    pub id: u32,
    pub state: String,
    pub host_id: u32,
    pub immutable_state: bool,
    pub not_deleted: Option<bool>,
    pub content_type_id: Option<u32>,
}

#[cfg(feature = "postgres-interop")]
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

#[derive(
    Debug, serde::Serialize, serde::Deserialize, Eq, PartialEq, Ord, PartialOrd, Clone, Hash,
)]
pub struct DeviceId(pub String);

#[cfg(feature = "postgres-interop")]
impl ToSql for DeviceId {
    fn to_sql(
        &self,
        ty: &Type,
        w: &mut BytesMut,
    ) -> Result<IsNull, Box<dyn std::error::Error + Sync + Send>> {
        <&str as ToSql>::to_sql(&&*self.0, ty, w)
    }

    fn accepts(ty: &Type) -> bool {
        <&str as ToSql>::accepts(ty)
    }

    to_sql_checked!();
}

#[cfg(feature = "postgres-interop")]
impl<'a> FromSql<'a> for DeviceId {
    fn from_sql(
        ty: &Type,
        raw: &'a [u8],
    ) -> Result<DeviceId, Box<dyn std::error::Error + Sync + Send>> {
        FromSql::from_sql(ty, raw).map(DeviceId)
    }

    fn accepts(ty: &Type) -> bool {
        <String as FromSql>::accepts(ty)
    }
}

impl Deref for DeviceId {
    type Target = String;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

#[derive(Debug, Default, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct DeviceIds(pub BTreeSet<DeviceId>);

impl Deref for DeviceIds {
    type Target = BTreeSet<DeviceId>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl DerefMut for DeviceIds {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.0
    }
}

#[cfg(feature = "postgres-interop")]
impl ToSql for DeviceIds {
    fn to_sql(
        &self,
        ty: &Type,
        w: &mut BytesMut,
    ) -> Result<IsNull, Box<dyn std::error::Error + Sync + Send>> {
        let xs = self.0.iter().collect::<Vec<_>>();
        <&[&DeviceId] as ToSql>::to_sql(&&*xs, ty, w)
    }

    fn accepts(ty: &Type) -> bool {
        <&[&DeviceId] as ToSql>::accepts(ty)
    }

    to_sql_checked!();
}

#[cfg(feature = "postgres-interop")]
impl<'a> FromSql<'a> for DeviceIds {
    fn from_sql(
        ty: &Type,
        raw: &'a [u8],
    ) -> Result<DeviceIds, Box<dyn std::error::Error + Sync + Send>> {
        <Vec<DeviceId> as FromSql>::from_sql(ty, raw).map(|xs| DeviceIds(xs.into_iter().collect()))
    }

    fn accepts(ty: &Type) -> bool {
        <Vec<DeviceId> as FromSql>::accepts(ty)
    }
}

#[derive(Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Size(pub u64);

#[cfg(feature = "postgres-interop")]
impl ToSql for Size {
    fn to_sql(
        &self,
        ty: &Type,
        w: &mut BytesMut,
    ) -> Result<IsNull, Box<dyn std::error::Error + Sync + Send>> {
        <&str as ToSql>::to_sql(&&*self.0.to_string(), ty, w)
    }

    fn accepts(ty: &Type) -> bool {
        <&str as ToSql>::accepts(ty)
    }

    to_sql_checked!();
}

#[cfg(feature = "postgres-interop")]
impl<'a> FromSql<'a> for Size {
    fn from_sql(
        ty: &Type,
        raw: &'a [u8],
    ) -> Result<Size, Box<dyn std::error::Error + Sync + Send>> {
        <String as FromSql>::from_sql(ty, raw).and_then(|x| {
            x.parse::<u64>()
                .map(Size)
                .map_err(|e| -> Box<dyn std::error::Error + Sync + Send> { Box::new(e) })
        })
    }

    fn accepts(ty: &Type) -> bool {
        <String as FromSql>::accepts(ty)
    }
}

/// The current type of Devices we support
#[derive(
    Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize,
)]
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

#[cfg(feature = "postgres-interop")]
impl ToSql for DeviceType {
    fn to_sql(
        &self,
        ty: &Type,
        w: &mut BytesMut,
    ) -> Result<IsNull, Box<dyn std::error::Error + Sync + Send>> {
        <String as ToSql>::to_sql(&format!("{}", self), ty, w)
    }

    fn accepts(ty: &Type) -> bool {
        <String as ToSql>::accepts(ty)
    }

    to_sql_checked!();
}

#[cfg(feature = "postgres-interop")]
impl<'a> FromSql<'a> for DeviceType {
    fn from_sql(
        ty: &Type,
        raw: &'a [u8],
    ) -> Result<DeviceType, Box<dyn std::error::Error + Sync + Send>> {
        FromSql::from_sql(ty, raw).and_then(|x| match x {
            "scsi" => Ok(DeviceType::ScsiDevice),
            "partition" => Ok(DeviceType::Partition),
            "mdraid" => Ok(DeviceType::MdRaid),
            "mpath" => Ok(DeviceType::Mpath),
            "vg" => Ok(DeviceType::VolumeGroup),
            "lv" => Ok(DeviceType::LogicalVolume),
            "zpool" => Ok(DeviceType::Zpool),
            "dataset" => Ok(DeviceType::Dataset),
            _ => {
                let e: Box<dyn std::error::Error + Sync + Send> = Box::new(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    "Unknown DeviceType variant",
                ));

                Err(e)
            }
        })
    }

    fn accepts(ty: &Type) -> bool {
        <String as FromSql>::accepts(ty)
    }
}

/// A device (Block or Virtual).
/// These should be unique per cluster
#[derive(Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Device {
    pub id: DeviceId,
    pub size: Size,
    pub usable_for_lustre: bool,
    pub device_type: DeviceType,
    pub parents: DeviceIds,
    pub children: DeviceIds,
}

pub const DEVICE_TABLE_NAME: TableName = TableName("chroma_core_device");

impl Name for Device {
    fn table_name() -> TableName<'static> {
        DEVICE_TABLE_NAME
    }
}

#[cfg(feature = "postgres-interop")]
impl From<Row> for Device {
    fn from(row: Row) -> Self {
        Device {
            id: row.get("id"),
            size: row.get("size"),
            usable_for_lustre: row.get("usable_for_lustre"),
            device_type: row.get("device_type"),
            parents: row.get("parents"),
            children: row.get("children"),
        }
    }
}

#[derive(Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Paths(pub BTreeSet<PathBuf>);

impl Deref for Paths {
    type Target = BTreeSet<PathBuf>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

#[cfg(feature = "postgres-interop")]
impl ToSql for Paths {
    fn to_sql(
        &self,
        ty: &Type,
        w: &mut BytesMut,
    ) -> Result<IsNull, Box<dyn std::error::Error + Sync + Send>> {
        let xs = self.iter().map(|x| x.to_string_lossy()).collect::<Vec<_>>();
        <&[std::borrow::Cow<'_, str>] as ToSql>::to_sql(&&*xs, ty, w)
    }

    fn accepts(ty: &Type) -> bool {
        <&[std::borrow::Cow<'_, str>] as ToSql>::accepts(ty)
    }

    to_sql_checked!();
}

#[cfg(feature = "postgres-interop")]
impl<'a> FromSql<'a> for Paths {
    fn from_sql(
        ty: &Type,
        raw: &'a [u8],
    ) -> Result<Paths, Box<dyn std::error::Error + Sync + Send>> {
        <Vec<String> as FromSql>::from_sql(ty, raw)
            .map(|xs| Paths(xs.into_iter().map(PathBuf::from).collect()))
    }

    fn accepts(ty: &Type) -> bool {
        <Vec<String> as FromSql>::accepts(ty)
    }
}

#[derive(Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct MountPath(pub Option<PathBuf>);

#[cfg(feature = "postgres-interop")]
impl ToSql for MountPath {
    fn to_sql(
        &self,
        ty: &Type,
        w: &mut BytesMut,
    ) -> Result<IsNull, Box<dyn std::error::Error + Sync + Send>> {
        <&Option<String> as ToSql>::to_sql(
            &&self.0.clone().map(|x| x.to_string_lossy().into_owned()),
            ty,
            w,
        )
    }

    fn accepts(ty: &Type) -> bool {
        <&Option<String> as ToSql>::accepts(ty)
    }

    to_sql_checked!();
}

#[cfg(feature = "postgres-interop")]
impl Deref for MountPath {
    type Target = Option<PathBuf>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

/// A pointer to a `Device` present on a host.
/// Stores mount_path and paths to reach the pointed to `Device`.
#[derive(Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct DeviceHost {
    pub device_id: DeviceId,
    pub fqdn: Fqdn,
    pub local: bool,
    pub paths: Paths,
    pub mount_path: MountPath,
    pub fs_type: Option<String>,
    pub fs_label: Option<String>,
    pub fs_uuid: Option<String>,
}

pub const DEVICE_HOST_TABLE_NAME: TableName = TableName("chroma_core_devicehost");

impl Name for DeviceHost {
    fn table_name() -> TableName<'static> {
        DEVICE_HOST_TABLE_NAME
    }
}

#[cfg(feature = "postgres-interop")]
impl From<Row> for DeviceHost {
    fn from(row: Row) -> Self {
        DeviceHost {
            device_id: row.get("device_id"),
            fqdn: Fqdn(row.get::<_, String>("fqdn")),
            local: row.get("local"),
            paths: row.get("paths"),
            mount_path: MountPath(
                row.get::<_, Option<String>>("mount_path")
                    .map(PathBuf::from),
            ),
            fs_type: row.get::<_, Option<String>>("fs_type"),
            fs_label: row.get::<_, Option<String>>("fs_label"),
            fs_uuid: row.get::<_, Option<String>>("fs_uuid"),
        }
    }
}
