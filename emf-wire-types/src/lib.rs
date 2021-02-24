// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod alert;
pub mod client;
pub mod corosync;
pub mod db;
pub mod filesystem;
pub mod graphql_duration;
pub mod high_availability;
pub mod host;
pub mod lnet;
pub mod ost_pool;
pub mod sfa;
pub mod snapshot;
pub mod state_machine;
pub mod stratagem;
pub mod target;
pub mod task;
pub mod warp_drive;

pub use alert::*;
use chrono::{DateTime, Utc};
pub use corosync::*;
use db::LogMessageRecord;
pub use filesystem::*;
pub use host::*;
use ipnetwork::{Ipv4Network, Ipv6Network};
pub use lnet::*;
pub use ost_pool::*;
pub use state_machine::*;
use std::{
    cmp::{Ord, Ordering},
    collections::{BTreeMap, HashMap},
    convert::TryFrom,
    convert::TryInto,
    fmt, io,
    num::ParseIntError,
    ops::Deref,
    sync::Arc,
};
pub use stratagem::*;
pub use target::*;

#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "postgres-interop", sqlx(type_name = "component"))]
#[cfg_attr(feature = "postgres-interop", sqlx(rename_all = "snake_case"))]
#[serde(rename_all = "snake_case")]
#[derive(
    PartialEq, Eq, Clone, Copy, Debug, serde::Serialize, serde::Deserialize, Ord, PartialOrd, Hash,
)]
pub enum ComponentType {
    Host,
    Filesystem,
    Lnet,
    Target,
    ClientMount,
    Ntp,
    Mgt,
    Ost,
    Mdt,
    MgtMdt,
}

impl fmt::Display for ComponentType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::Host => "host",
            Self::Filesystem => "filesystem",
            Self::Lnet => "lnet",
            Self::Target => "target",
            Self::ClientMount => "client_mount",
            Self::Ntp => "ntp",
            Self::Mgt => "mgt",
            Self::Ost => "ost",
            Self::Mdt => "mdt",
            Self::MgtMdt => "mgt_mdt",
        };

        write!(f, "{}", x)
    }
}

#[derive(Eq, PartialEq, Hash, Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct PluginName(pub String);

impl From<PluginName> for String {
    fn from(PluginName(s): PluginName) -> Self {
        s
    }
}

impl From<&str> for PluginName {
    fn from(name: &str) -> Self {
        Self(name.into())
    }
}

impl fmt::Display for PluginName {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(
    Eq, PartialEq, Ord, PartialOrd, Hash, Debug, Clone, serde::Serialize, serde::Deserialize,
)]
#[serde(transparent)]
pub struct Fqdn(pub String);

impl From<Fqdn> for String {
    fn from(Fqdn(s): Fqdn) -> Self {
        s
    }
}

impl From<&str> for Fqdn {
    fn from(s: &str) -> Self {
        Fqdn(s.into())
    }
}

impl From<&String> for Fqdn {
    fn from(s: &String) -> Self {
        Fqdn(s.as_str().into())
    }
}

impl From<String> for Fqdn {
    fn from(s: String) -> Self {
        Fqdn(s)
    }
}

impl fmt::Display for Fqdn {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl Deref for Fqdn {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        self.0.as_str()
    }
}

#[derive(
    Eq, PartialEq, Ord, PartialOrd, Hash, Debug, Clone, serde::Serialize, serde::Deserialize,
)]
#[serde(transparent)]
pub struct MachineId(pub String);

impl From<MachineId> for String {
    fn from(MachineId(s): MachineId) -> Self {
        s
    }
}

impl From<&str> for MachineId {
    fn from(s: &str) -> Self {
        Self(s.into())
    }
}

impl From<&String> for MachineId {
    fn from(s: &String) -> Self {
        Self(s.as_str().into())
    }
}

impl From<String> for MachineId {
    fn from(s: String) -> Self {
        Self(s)
    }
}

impl fmt::Display for MachineId {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl Deref for MachineId {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        self.0.as_str()
    }
}

#[derive(Debug, Clone, Eq, PartialEq, Hash, serde::Deserialize, serde::Serialize)]
pub struct ActionName(pub String);

impl From<&str> for ActionName {
    fn from(name: &str) -> Self {
        Self(name.into())
    }
}

impl From<&String> for ActionName {
    fn from(name: &String) -> Self {
        Self(name.as_str().into())
    }
}

impl Deref for ActionName {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        self.0.as_str()
    }
}

impl From<String> for ActionName {
    fn from(name: String) -> Self {
        Self(name)
    }
}

impl fmt::Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct ActionId(pub String);

impl fmt::Display for ActionId {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Things we can do with actions
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone, PartialEq)]
#[serde(tag = "type")]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Action {
    ActionStart {
        action: ActionName,
        args: serde_json::value::Value,
        id: ActionId,
    },
    ActionCancel {
        id: ActionId,
    },
}

impl Action {
    pub fn get_id(&self) -> &ActionId {
        match self {
            Self::ActionStart { id, .. } | Self::ActionCancel { id, .. } => id,
        }
    }
}

impl TryFrom<Action> for serde_json::Value {
    type Error = serde_json::Error;

    fn try_from(action: Action) -> Result<Self, Self::Error> {
        serde_json::to_value(action)
    }
}

/// Actions can be run either locally or remotely.
/// Besides the node these are run on, the interface should
/// be the same.
///
/// This should probably be collapsed into a single struct over an enum at some point.
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ActionType {
    Remote((Fqdn, Action)),
    Local(Action),
}

/// The result of running the action on an agent.
#[derive(serde::Deserialize, serde::Serialize, Debug)]
pub struct ActionResult {
    pub id: ActionId,
    pub result: Result<serde_json::value::Value, String>,
}

pub type AgentResult = std::result::Result<serde_json::Value, String>;

pub trait ToJsonValue {
    fn to_json_value(&self) -> Result<serde_json::Value, String>;
}

impl<T: serde::Serialize> ToJsonValue for T {
    fn to_json_value(&self) -> Result<serde_json::Value, String> {
        serde_json::to_value(self).map_err(|e| format!("{:?}", e))
    }
}

pub trait ToBytes {
    fn to_bytes(&self) -> Result<Vec<u8>, serde_json::error::Error>;
}

impl<T: serde::Serialize> ToBytes for T {
    fn to_bytes(&self) -> Result<Vec<u8>, serde_json::error::Error> {
        serde_json::to_vec(&self)
    }
}

/// Arguments to all Task Actions on agents: FSNAME, Task Args, FID LIST
#[derive(serde::Deserialize, serde::Serialize, Debug)]
pub struct TaskAction(pub String, pub HashMap<String, String>, pub Vec<FidItem>);

#[derive(
    serde::Serialize, serde::Deserialize, Clone, Copy, Debug, Eq, PartialEq, PartialOrd, Ord, Hash,
)]
pub struct CompositeId(pub ComponentType, pub i32);

impl fmt::Display for CompositeId {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{:?}:{}", self.0, self.1)
    }
}

pub trait ToCompositeId {
    fn composite_id(&self) -> CompositeId;
}

impl<T: db::Id + ToComponentType> ToCompositeId for T {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.component_type(), self.id())
    }
}

/// A `Record` with it's concrete type erased.
/// The returned item implements the `Label` and `EndpointName`
/// traits.
pub trait ErasedRecord: Label + db::Id + core::fmt::Debug {}
impl<T: Label + db::Id + ToCompositeId + core::fmt::Debug> ErasedRecord for T {}

impl<T: ToCompositeId> ToCompositeId for &Arc<T> {
    fn composite_id(&self) -> CompositeId {
        let t: &T = self.deref();

        t.composite_id()
    }
}

impl<T: ToCompositeId> ToCompositeId for Arc<T> {
    fn composite_id(&self) -> CompositeId {
        let t: &T = self.deref();

        t.composite_id()
    }
}

pub trait ToComponentType {
    fn component_type(&self) -> ComponentType;
}

pub trait Label {
    fn label(&self) -> &str;
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct Conf {
    pub allow_anonymous_read: bool,
    pub build: String,
    pub version: String,
    pub exa_version: Option<String>,
    pub is_release: bool,
    pub branding: Branding,
    pub use_stratagem: bool,
    pub use_snapshots: bool,
    pub monitor_sfa: bool,
}

impl Default for Conf {
    fn default() -> Self {
        Self {
            allow_anonymous_read: true,
            build: "Not Loaded".into(),
            version: "0".into(),
            exa_version: None,
            is_release: false,
            branding: Branding::default(),
            use_stratagem: false,
            use_snapshots: false,
            monitor_sfa: false,
        }
    }
}

/// A `NtpConfiguration` record from `/api/ntp_configuration/`
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct NtpConfiguration {
    pub content_type_id: i32,
    pub id: i32,
    pub immutable_state: bool,
    pub label: String,
    pub not_deleted: Option<bool>,
    pub resource_uri: String,
    pub state: String,
    pub state_modified_at: String,
}

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct ClientMount {
    pub filesystem_name: String,
    pub mountpoints: Vec<String>,
    pub state: String,
}

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct FilesystemConfParams {
    #[serde(rename = "llite.max_cached_mb")]
    pub llite_max_cached_mb: Option<String>,
    #[serde(rename = "llite.max_read_ahead_mb")]
    pub llite_max_read_ahead_mb: Option<String>,
    #[serde(rename = "llite.max_read_ahead_whole_mb")]
    pub llite_max_read_ahead_whole_mb: Option<String>,
    #[serde(rename = "llite.statahead_max")]
    pub llite_statahead_max: Option<String>,
    #[serde(rename = "sys.at_early_margin")]
    pub sys_at_early_margin: Option<String>,
    #[serde(rename = "sys.at_extra")]
    pub sys_at_extra: Option<String>,
    #[serde(rename = "sys.at_history")]
    pub sys_at_history: Option<String>,
    #[serde(rename = "sys.at_max")]
    pub sys_at_max: Option<String>,
    #[serde(rename = "sys.at_min")]
    pub sys_at_min: Option<String>,
    #[serde(rename = "sys.ldlm_timeout")]
    pub sys_ldlm_timeout: Option<String>,
    #[serde(rename = "sys.timeout")]
    pub sys_timeout: Option<String>,
}

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct MdtConfParams {
    #[serde(rename = "lov.qos_prio_free")]
    lov_qos_prio_free: Option<String>,
    #[serde(rename = "lov.qos_threshold_rr")]
    lov_qos_threshold_rr: Option<String>,
    #[serde(rename = "lov.stripecount")]
    lov_stripecount: Option<String>,
    #[serde(rename = "lov.stripesize")]
    lov_stripesize: Option<String>,
    #[serde(rename = "mdt.MDS.mds.threads_max")]
    mdt_mds_mds_threads_max: Option<String>,
    #[serde(rename = "mdt.MDS.mds.threads_min")]
    mdt_mds_mds_threads_min: Option<String>,
    #[serde(rename = "mdt.MDS.mds_readpage.threads_max")]
    mdt_mds_mds_readpage_threads_max: Option<String>,
    #[serde(rename = "mdt.MDS.mds_readpage.threads_min")]
    mdt_mds_mds_readpage_threads_min: Option<String>,
    #[serde(rename = "mdt.MDS.mds_setattr.threads_max")]
    mdt_mds_mds_setattr_threads_max: Option<String>,
    #[serde(rename = "mdt.MDS.mds_setattr.threads_min")]
    mdt_mds_mds_setattr_threads_min: Option<String>,
    #[serde(rename = "mdt.hsm_control")]
    mdt_hsm_control: Option<String>,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Substitution {
    pub start: String,
    pub end: String,
    pub label: String,
    pub resource_uri: String,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq, Eq)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
#[repr(i16)]
pub enum MessageClass {
    Normal = 0,
    Lustre = 1,
    LustreError = 2,
}

impl TryFrom<i16> for MessageClass {
    type Error = &'static str;

    fn try_from(value: i16) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(MessageClass::Normal),
            1 => Ok(MessageClass::Lustre),
            2 => Ok(MessageClass::LustreError),
            _ => Err("Invalid variant for MessageClass"),
        }
    }
}

/// Severities from syslog protocol
///
/// | Code | Severity                                 |
/// |------|------------------------------------------|
/// | 0    | Emergency: system is unusable            |
/// | 1    | Alert: action must be taken immediately  |
/// | 2    | Critical: critical conditions            |
/// | 3    | Error: error conditions                  |
/// | 4    | Warning: warning conditions              |
/// | 5    | Notice: normal but significant condition |
/// | 6    | Informational: informational messages    |
/// | 7    | Debug: debug-level messages              |
///
#[derive(
    serde::Deserialize, serde::Serialize, PartialEq, Eq, Ord, PartialOrd, Clone, Copy, Debug,
)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
#[repr(i16)]
pub enum LogSeverity {
    Emergency = 0,
    Alert = 1,
    Critical = 2,
    Error = 3,
    Warning = 4,
    Notice = 5,
    Informational = 6,
    Debug = 7,
}

impl TryFrom<i16> for LogSeverity {
    type Error = &'static str;

    fn try_from(value: i16) -> Result<Self, <Self as TryFrom<i16>>::Error> {
        match value {
            0 => Ok(LogSeverity::Emergency),
            1 => Ok(LogSeverity::Alert),
            2 => Ok(LogSeverity::Critical),
            3 => Ok(LogSeverity::Error),
            4 => Ok(LogSeverity::Warning),
            5 => Ok(LogSeverity::Notice),
            6 => Ok(LogSeverity::Informational),
            7 => Ok(LogSeverity::Debug),
            _ => Err("Invalid variant for LogSeverity"),
        }
    }
}

/// An Log record from /api/log/
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Log {
    pub datetime: String,
    pub facility: i32,
    pub fqdn: String,
    pub id: i32,
    pub message: String,
    pub message_class: MessageClass,
    pub resource_uri: String,
    pub severity: LogSeverity,
    pub substitutions: Vec<Substitution>,
    pub tag: String,
}

// A log message from GraphQL endpoint
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct LogMessage {
    pub id: i32,
    pub datetime: chrono::DateTime<Utc>,
    pub facility: i32,
    pub fqdn: String,
    pub message: String,
    pub message_class: MessageClass,
    pub severity: LogSeverity,
    pub tag: String,
}

impl TryFrom<LogMessageRecord> for LogMessage {
    type Error = &'static str;

    fn try_from(record: LogMessageRecord) -> Result<Self, Self::Error> {
        Ok(Self {
            id: record.id,
            datetime: record.datetime,
            facility: record.facility as i32,
            fqdn: record.fqdn,
            message: record.message,
            message_class: record.message_class.try_into()?,
            severity: record.severity.try_into()?,
            tag: record.tag,
        })
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SortDir {
    Asc,
    Desc,
}

impl Default for SortDir {
    fn default() -> Self {
        Self::Asc
    }
}

impl Deref for SortDir {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        match self {
            Self::Asc => "ASC",
            Self::Desc => "DESC",
        }
    }
}

pub mod logs {
    use crate::LogMessage;

    #[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
    #[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
    pub struct Meta {
        pub total_count: i32,
    }

    #[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
    #[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
    pub struct LogResponse {
        pub data: Vec<LogMessage>,
        pub meta: Meta,
    }
}

/// An `AlertType` record from `api/alert_type`.
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug, Eq, PartialEq)]
pub struct AlertType {
    pub description: String,
    pub id: String,
    pub resource_uri: String,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Copy, Debug, Eq, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum GroupType {
    Superusers,
    FilesystemAdministrators,
    FilesystemUsers,
}

/// A `Group` record from `api/group`.
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug, Eq, PartialEq)]
pub struct Group {
    pub id: i32,
    pub name: GroupType,
    pub resource_uri: String,
}

/// A `User` record from `api/user`.
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug, Eq, PartialEq)]
pub struct User {
    pub email: String,
    pub first_name: String,
    pub full_name: String,
    pub groups: Option<Vec<Group>>,
    pub id: i32,
    pub is_superuser: bool,
    pub last_name: String,
    pub new_password1: Option<String>,
    pub new_password2: Option<String>,
    pub password1: Option<String>,
    pub password2: Option<String>,
    pub resource_uri: String,
    pub username: String,
}

pub mod time {
    #[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
    pub enum Synced {
        Synced,
        Unsynced,
    }

    #[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize)]
    pub enum State {
        None,
        Multiple,
        Synced,
        Unsynced(Option<Offset>),
        Unknown,
    }

    #[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize)]
    pub struct Offset(String);

    impl<T: ToString> From<T> for Offset {
        fn from(s: T) -> Self {
            Self(s.to_string())
        }
    }
}

/// Types used for component checks
#[derive(Debug, Default, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ElementState {
    pub name: String,
    pub configurable: bool,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum UnitFileState {
    Disabled,
    Enabled,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ActiveState {
    Inactive,
    Active,
    Activating,
    Failed,
}

#[derive(Debug, Clone, Eq, PartialEq, PartialOrd, Ord, serde::Serialize, serde::Deserialize)]
pub enum RunState {
    Stopped,
    Enabled,
    Activating,
    Failed,
    Started,
    Setup, // Enabled + Started
}

impl Default for RunState {
    fn default() -> Self {
        Self::Stopped
    }
}

#[derive(Debug, Clone, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ServiceState {
    Unconfigured,
    Configured(RunState),
}

impl Default for ServiceState {
    fn default() -> Self {
        Self::Unconfigured
    }
}

impl fmt::Display for ServiceState {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::Unconfigured => f.pad(&format!("{:?}", self)),
            Self::Configured(r) => f.pad(&format!("{:?}", r)),
        }
    }
}

/// standard:provider:ocftype (e.g. ocf:heartbeat:ZFS, or stonith:fence_ipmilan)
#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct ResourceAgentType {
    // e.g. ocf, lsb, stonith, etc..
    pub standard: String,
    // e.g. heartbeat, lustre, chroma
    pub provider: Option<String>,
    // e.g. Lustre, ZFS
    pub ocftype: String,
}

impl ResourceAgentType {
    pub fn new<'a>(
        standard: impl Into<Option<&'a str>>,
        provider: impl Into<Option<&'a str>>,
        ocftype: impl Into<Option<&'a str>>,
    ) -> Self {
        Self {
            standard: standard.into().map(str::to_string).unwrap_or_default(),
            provider: provider.into().map(str::to_string),
            ocftype: ocftype.into().map(str::to_string).unwrap_or_default(),
        }
    }
}

impl fmt::Display for ResourceAgentType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.provider {
            Some(provider) => write!(f, "{}:{}:{}", self.standard, provider, self.ocftype),
            None => write!(f, "{}:{}", self.standard, self.ocftype),
        }
    }
}

/// Information about pacemaker resource agents
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ResourceAgentInfo {
    pub agent: ResourceAgentType,
    pub id: String,
    pub args: HashMap<String, String>,
    pub ops: PacemakerOperations,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum OrderingKind {
    Mandatory,
    Optional,
    Serialize,
}

impl fmt::Display for OrderingKind {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        f.pad(&format!("{:?}", self))
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PacemakerScore {
    Infinity,
    Value(i32),
    NegInfinity,
}

impl fmt::Display for PacemakerScore {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            PacemakerScore::Value(v) => write!(f, "{}", v),
            PacemakerScore::Infinity => write!(f, "INFINITY"),
            PacemakerScore::NegInfinity => write!(f, "-INFINITY"),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PacemakerKindOrScore {
    Kind(OrderingKind),
    Score(PacemakerScore),
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct PacemakerOperations {
    // Time to wait for Resource to start
    pub start: Option<String>,
    // Time of monitor interval
    pub monitor: Option<String>,
    // Time to wait for Resource to stop
    pub stop: Option<String>,
}

impl PacemakerOperations {
    pub fn new(
        start: impl Into<Option<String>>,
        monitor: impl Into<Option<String>>,
        stop: impl Into<Option<String>>,
    ) -> Self {
        Self {
            start: start.into(),
            monitor: monitor.into(),
            stop: stop.into(),
        }
    }

    pub fn is_any_some(&self) -> bool {
        self.start.is_some() || self.stop.is_some() || self.monitor.is_some()
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LossPolicy {
    Stop,
    Demote,
    Fence,
    Freeze,
}

impl fmt::Display for LossPolicy {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            LossPolicy::Stop => write!(f, "stop"),
            LossPolicy::Demote => write!(f, "demote"),
            LossPolicy::Fence => write!(f, "fence"),
            LossPolicy::Freeze => write!(f, "freeze"),
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PacemakerActions {
    Start,
    Promote,
    Demote,
    Stop,
}

impl fmt::Display for PacemakerActions {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            PacemakerActions::Demote => write!(f, "demote"),
            PacemakerActions::Promote => write!(f, "promote"),
            PacemakerActions::Start => write!(f, "start"),
            PacemakerActions::Stop => write!(f, "stop"),
        }
    }
}

/// Information about pacemaker resource agents
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ResourceConstraint {
    Order {
        id: String,
        first: String,
        first_action: Option<PacemakerActions>,
        then: String,
        then_action: Option<PacemakerActions>,
        // While the documentation only lists Kind the xml schema
        // (constraints-2.9.rng) shows Kind or Score being valid
        kind: Option<PacemakerKindOrScore>,
    },
    Location {
        id: String,
        rsc: String,
        node: String,
        score: PacemakerScore,
    },
    Colocation {
        id: String,
        rsc: String,
        with_rsc: String,
        score: PacemakerScore,
    },
    Ticket {
        id: String,
        rsc: String,
        ticket: String,
        loss_policy: Option<LossPolicy>,
    },
}

#[derive(Debug, Clone, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ConfigState {
    Unknown,
    Default,
    // components is in default configuration
    EMF,
    // matches what EMF would do
    Other,
}

impl Default for ConfigState {
    fn default() -> Self {
        Self::Unknown
    }
}

impl fmt::Display for ConfigState {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        f.pad(&format!("{:?}", self))
    }
}

#[derive(Debug, Default, PartialEq, Clone, serde::Serialize, serde::Deserialize)]
pub struct ComponentState<T: Default> {
    pub service: ServiceState,
    pub config: ConfigState,
    pub elements: Vec<ElementState>,
    pub info: String,
    pub state: T,
}

#[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct JournalMessage {
    pub datetime: std::time::Duration,
    pub severity: JournalPriority,
    pub facility: i16,
    pub source: String,
    pub message: String,
}

#[derive(Debug, PartialEq, serde::Deserialize, serde::Serialize)]
#[repr(i16)]
pub enum JournalPriority {
    Emerg,
    Alert,
    Crit,
    Err,
    Warning,
    Notice,
    Info,
    Debug,
}

impl TryFrom<String> for JournalPriority {
    type Error = io::Error;

    fn try_from(s: String) -> Result<Self, Self::Error> {
        let x = s
            .parse::<u8>()
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        match x {
            0 => Ok(Self::Emerg),
            1 => Ok(Self::Alert),
            2 => Ok(Self::Crit),
            3 => Ok(Self::Err),
            4 => Ok(Self::Warning),
            5 => Ok(Self::Notice),
            6 => Ok(Self::Info),
            7 => Ok(Self::Debug),
            x => Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("Priority {} not in range", x),
            )),
        }
    }
}

#[derive(Debug, Clone, Copy, serde::Serialize, serde::Deserialize)]
pub enum Branding {
    DDN(DdnBranding),
    Whamcloud,
}

#[derive(Debug, Clone, Copy, serde::Serialize, serde::Deserialize)]
pub enum DdnBranding {
    AI200,
    AI200X,
    AI400,
    AI400X,
    AI7990X,
    ES14K,
    ES14KX,
    ES18K,
    ES18KX,
    ES200NV,
    ES200NVX,
    ES400NV,
    ES400NVX,
    ES7990,
    ES7990X,
    Exascaler,
}

impl fmt::Display for DdnBranding {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::AI200 => write!(f, "AI200"),
            Self::AI200X => write!(f, "AI200X"),
            Self::AI400 => write!(f, "AI400"),
            Self::AI400X => write!(f, "AI400X"),
            Self::AI7990X => write!(f, "AI7990X"),
            Self::ES14K => write!(f, "ES14K"),
            Self::ES14KX => write!(f, "ES14KX"),
            Self::ES18K => write!(f, "ES18K"),
            Self::ES18KX => write!(f, "ES18KX"),
            Self::ES200NV => write!(f, "ES200NV"),
            Self::ES200NVX => write!(f, "ES200NVX"),
            Self::ES400NV => write!(f, "ES400NV"),
            Self::ES400NVX => write!(f, "ES400NVX"),
            Self::ES7990 => write!(f, "ES7990"),
            Self::ES7990X => write!(f, "ES7990X"),
            Self::Exascaler => write!(f, "EXA5"),
        }
    }
}

impl Default for Branding {
    fn default() -> Self {
        Self::Whamcloud
    }
}

impl From<String> for Branding {
    fn from(x: String) -> Self {
        match x.to_lowercase().as_str() {
            "ai200" => Self::DDN(DdnBranding::AI200),
            "ai200x" => Self::DDN(DdnBranding::AI200X),
            "ai400" => Self::DDN(DdnBranding::AI400),
            "ai400x" => Self::DDN(DdnBranding::AI400X),
            "ai7990x" => Self::DDN(DdnBranding::AI7990X),
            "es14k" => Self::DDN(DdnBranding::ES14K),
            "es14kx" => Self::DDN(DdnBranding::ES14KX),
            "es18k" => Self::DDN(DdnBranding::ES18K),
            "es18kx" => Self::DDN(DdnBranding::ES18KX),
            "es200nv" => Self::DDN(DdnBranding::ES200NV),
            "es200nvx" => Self::DDN(DdnBranding::ES200NVX),
            "es400nv" => Self::DDN(DdnBranding::ES400NV),
            "es400nvx" => Self::DDN(DdnBranding::ES400NVX),
            "es7990" => Self::DDN(DdnBranding::ES7990),
            "es7990x" => Self::DDN(DdnBranding::ES7990X),
            "exascaler" => Self::DDN(DdnBranding::Exascaler),
            _ => Self::Whamcloud,
        }
    }
}

impl fmt::Display for Branding {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::DDN(x) => write!(f, "{}", x),
            Self::Whamcloud => write!(f, "whamcloud"),
        }
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FidError {
    pub fid: String,
    pub data: serde_json::Value,
    pub errno: i16,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FidItem {
    pub fid: String,
    pub data: serde_json::Value,
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct LustreClient {
    pub id: i32,
    pub state_modified_at: DateTime<Utc>,
    pub state: String,
    pub filesystem: String,
    pub host_id: i32,
    pub mountpoints: Vec<String>,
}

#[derive(Debug, Eq, Clone, serde::Serialize, serde::Deserialize)]
pub struct LdevEntry {
    pub primary: String,
    pub failover: Option<String>,
    pub label: String,
    pub device: String,
    pub fs_type: Option<FsType>,
}

impl From<&str> for LdevEntry {
    fn from(x: &str) -> Self {
        let parts: Vec<&str> = x.split(' ').collect();

        Self {
            primary: (*parts
                .get(0)
                .expect("LdevEntry must specify a primary server."))
            .to_string(),
            failover: parts.get(1).map_or_else(
                || panic!("LdevEntry must specify a failover server or '-'."),
                |x| {
                    if *x == "-" {
                        None
                    } else {
                        Some((*x).to_string())
                    }
                },
            ),
            label: (*parts.get(2).expect("LdevEntry must specify a label.")).to_string(),
            device: (*parts.get(3).expect("LdevEntry must specify a device.")).to_string(),
            fs_type: FsType::try_from(
                (*parts.get(3).expect("LdevEntry must specify a device."))
                    .split(':')
                    .next()
                    .expect("get fs_type"),
            )
            .ok(),
        }
    }
}

impl fmt::Display for LdevEntry {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let device = if self.device.starts_with("zfs:") || self.device.starts_with("ldiskfs:") {
            self.device.to_string()
        } else if self.fs_type == Some(FsType::Zfs) {
            format!("zfs:{}", self.device)
        } else if self.fs_type == Some(FsType::Ldiskfs) {
            format!("ldiskfs:{}", self.device)
        } else {
            self.device.to_string()
        };

        write!(
            f,
            "{} {} {} {}",
            self.primary,
            self.failover.as_deref().unwrap_or("-"),
            self.label,
            device
        )
    }
}

impl Ord for LdevEntry {
    fn cmp(&self, other: &Self) -> Ordering {
        self.label.cmp(&other.label)
    }
}

impl PartialOrd for LdevEntry {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for LdevEntry {
    fn eq(&self, other: &Self) -> bool {
        self.label == other.label
    }
}

#[derive(Clone, Copy, PartialEq, Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LndType {
    Tcp,
    O2ib,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LinuxType {
    Ethernet,
    Ether,
    Infiniband,
}

impl fmt::Display for LndType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Tcp => write!(f, "tcp"),
            Self::O2ib => write!(f, "o2ib"),
        }
    }
}

#[derive(Debug)]
pub struct InterfaceError(pub String);

impl fmt::Display for InterfaceError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for InterfaceError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

impl TryFrom<Option<String>> for LinuxType {
    type Error = InterfaceError;

    fn try_from(val: Option<String>) -> Result<Self, Self::Error> {
        if let Some(val) = val {
            match val.to_ascii_lowercase().trim() {
                "ethernet" => Ok(LinuxType::Ethernet),
                "ether" => Ok(LinuxType::Ether),
                "infiniband" => Ok(LinuxType::Infiniband),
                _ => Err(InterfaceError("Invalid linux network type. Must be one of 'ethernet', 'ether', or 'infiniband'.".into())),
            }
        } else {
            Err(InterfaceError("Interface type is not set.".into()))
        }
    }
}

impl TryFrom<Option<LinuxType>> for LndType {
    type Error = InterfaceError;

    fn try_from(i_type: Option<LinuxType>) -> Result<Self, Self::Error> {
        if let Some(i_type) = i_type {
            match i_type {
                LinuxType::Ethernet => Ok(LndType::Tcp),
                LinuxType::Ether => Ok(LndType::Tcp),
                LinuxType::Infiniband => Ok(LndType::O2ib),
            }
        } else {
            Err(InterfaceError(
                "The linux type is not set and thus cannot be converted to an LndType.".into(),
            ))
        }
    }
}

pub type StatResult = Result<u64, ParseIntError>;

#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct RxStats {
    pub bytes: u64,
    pub packets: u64,
    pub errs: u64,
    pub drop: u64,
    pub fifo: u64,
    pub frame: u64,
    pub compressed: u64,
    pub multicast: u64,
}

impl
    TryFrom<(
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
    )> for RxStats
{
    type Error = ParseIntError;

    fn try_from(
        (v1, v2, v3, v4, v5, v6, v7, v8): (
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
        ),
    ) -> Result<Self, Self::Error> {
        Ok(RxStats {
            bytes: v1?,
            packets: v2?,
            errs: v3?,
            drop: v4?,
            fifo: v5?,
            frame: v6?,
            compressed: v7?,
            multicast: v8?,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct TxStats {
    pub bytes: u64,
    pub packets: u64,
    pub errs: u64,
    pub drop: u64,
    pub fifo: u64,
    pub colls: u64,
    pub carrier: u64,
    pub compressed: u64,
}

impl
    TryFrom<(
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
    )> for TxStats
{
    type Error = ParseIntError;

    fn try_from(
        (v1, v2, v3, v4, v5, v6, v7, v8): (
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
            StatResult,
        ),
    ) -> Result<Self, Self::Error> {
        Ok(TxStats {
            bytes: v1?,
            packets: v2?,
            errs: v3?,
            drop: v4?,
            fifo: v5?,
            colls: v6?,
            carrier: v7?,
            compressed: v8?,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct InterfaceStats {
    pub rx: RxStats,
    pub tx: TxStats,
}

impl
    TryFrom<(
        Result<RxStats, ParseIntError>,
        Result<TxStats, ParseIntError>,
    )> for InterfaceStats
{
    type Error = ParseIntError;

    fn try_from(
        (rx, tx): (
            Result<RxStats, ParseIntError>,
            Result<TxStats, ParseIntError>,
        ),
    ) -> Result<Self, Self::Error> {
        Ok(InterfaceStats { rx: rx?, tx: tx? })
    }
}

#[derive(Clone, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct NetworkInterface {
    pub interface: String,
    pub mac_address: Option<String>,
    pub interface_type: Option<LndType>,
    pub inet4_address: Vec<Ipv4Network>,
    pub inet6_address: Vec<Ipv6Network>,
    pub stats: Option<InterfaceStats>,
    pub is_up: bool,
    pub is_slave: bool,
}

#[derive(Clone, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Nid {
    pub nid: String,
    pub status: String,
    pub interfaces: Option<BTreeMap<i32, String>>,
}

#[derive(Clone, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Net {
    #[serde(rename = "net type")]
    pub net_type: String,
    #[serde(rename = "local NI(s)")]
    pub local_nis: Vec<Nid>,
}

#[derive(Clone, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct LNet {
    pub net: Vec<Net>,
}

pub trait LNetState {
    fn get_state(&self) -> String;
}

impl LNetState for LNet {
    fn get_state(&self) -> String {
        let up = self
            .net
            .iter()
            .flat_map(|x| {
                x.local_nis
                    .iter()
                    .map(|x| x.status.as_str())
                    .collect::<Vec<&str>>()
            })
            .any(|x| x.to_ascii_lowercase() == "up");

        match up {
            true => "up".into(),
            false => "down".into(),
        }
    }
}

#[derive(PartialEq, serde::Serialize, serde::Deserialize)]
pub struct NetworkData {
    pub network_interfaces: Vec<NetworkInterface>,
    pub lnet_data: LNet,
}

#[derive(Hash, Eq, PartialEq)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
/// A Lustre Target and it's corresponding resource
pub struct TargetResource {
    /// The id of the cluster
    pub cluster_id: i32,
    /// The filesystems associated with this target
    pub fs_names: Vec<String>,
    /// The uuid of this target
    pub uuid: String,
    /// The name of this target
    pub name: String,
    /// The corosync resource id associated with this target
    pub resource_id: String,
    /// The id of this target
    pub target_id: i32,
    /// The current state of this target
    pub state: String,
    /// The list of host ids this target could possibly run on
    pub cluster_hosts: Vec<i32>,
}

pub struct BannedTargetResource {
    pub resource: String,
    pub cluster_id: i32,
    pub host_id: i32,
    pub mount_point: Option<String>,
}

#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
/// A Corosync banned resource
pub struct BannedResource {
    // The primary id
    pub id: i32,
    /// The resource name
    pub name: String,
    /// The id of the cluster in which the resource lives
    pub cluster_id: i32,
    /// The resource name
    pub resource: String,
    /// The node in which the resource lives
    pub node: String,
    /// The assigned weight of the resource
    pub weight: i32,
    /// Is master only
    pub master_only: bool,
}
