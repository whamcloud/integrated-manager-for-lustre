// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde_json;
use std::fmt;

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

#[derive(Eq, PartialEq, Hash, Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct Fqdn(pub String);

impl From<Fqdn> for String {
    fn from(Fqdn(s): Fqdn) -> Self {
        s
    }
}

impl fmt::Display for Fqdn {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct Id(pub String);

impl From<&str> for Id {
    fn from(name: &str) -> Self {
        Self(name.into())
    }
}

impl fmt::Display for Id {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct Seq(pub u64);

impl From<u64> for Seq {
    fn from(name: u64) -> Self {
        Self(name)
    }
}

impl Default for Seq {
    fn default() -> Self {
        Self(0)
    }
}

impl Seq {
    pub fn increment(&mut self) {
        self.0 += 1;
    }
}

/// The payload from the agent.
/// One or many can be packed into an `Envelope`
#[derive(serde::Serialize, serde::Deserialize, Debug)]
#[serde(tag = "type")]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Message {
    Data {
        fqdn: Fqdn,
        plugin: PluginName,
        session_id: Id,
        session_seq: Seq,
        body: serde_json::Value,
    },
    SessionCreateRequest {
        fqdn: Fqdn,
        plugin: PluginName,
    },
}

/// `Envelope` of `Messages` sent to the manager.
#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct Envelope {
    pub messages: Vec<Message>,
    pub server_boot_time: String,
    pub client_start_time: String,
}

impl Envelope {
    pub fn new(
        messages: Vec<Message>,
        client_start_time: impl Into<String>,
        server_boot_time: impl Into<String>,
    ) -> Self {
        Self {
            messages,
            server_boot_time: server_boot_time.into(),
            client_start_time: client_start_time.into(),
        }
    }
}

#[derive(serde::Deserialize, serde::Serialize, Debug)]
#[serde(tag = "type")]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ManagerMessage {
    SessionCreateResponse {
        fqdn: Fqdn,
        plugin: PluginName,
        session_id: Id,
    },
    Data {
        fqdn: Fqdn,
        plugin: PluginName,
        session_id: Id,
        body: serde_json::Value,
    },
    SessionTerminate {
        fqdn: Fqdn,
        plugin: PluginName,
        session_id: Id,
    },
    SessionTerminateAll {
        fqdn: Fqdn,
    },
}

#[derive(serde::Deserialize, serde::Serialize, Debug)]
pub struct ManagerMessages {
    pub messages: Vec<ManagerMessage>,
}

#[derive(serde::Deserialize, serde::Serialize, Debug)]
#[serde(tag = "type")]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PluginMessage {
    SessionTerminate {
        fqdn: Fqdn,
        plugin: PluginName,
        session_id: Id,
    },
    SessionCreate {
        fqdn: Fqdn,
        plugin: PluginName,
        session_id: Id,
    },
    Data {
        fqdn: Fqdn,
        plugin: PluginName,
        session_id: Id,
        session_seq: Seq,
        body: serde_json::Value,
    },
}

#[derive(Debug, Clone, Eq, PartialEq, Hash, serde::Deserialize, serde::Serialize)]
pub struct ActionName(pub String);

impl From<&str> for ActionName {
    fn from(name: &str) -> Self {
        Self(name.into())
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
            Action::ActionStart { id, .. } | Action::ActionCancel { id, .. } => id,
        }
    }
}

impl From<Action> for serde_json::Value {
    fn from(action: Action) -> Self {
        serde_json::to_value(action).unwrap()
    }
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

pub struct CompositeId(pub u32, pub u32);

impl fmt::Display for CompositeId {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}:{}", self.0, self.1)
    }
}

pub trait ToCompositeId {
    fn composite_id(&self) -> CompositeId;
}

pub trait Label {
    fn label(&self) -> &str;
}

pub trait EndpointName {
    fn endpoint_name() -> &'static str;
}

/// The type of lock
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, Eq, PartialEq, Hash)]
#[serde(rename_all = "lowercase")]
pub enum LockType {
    Read,
    Write,
}

/// The Action associated with a `LockChange`
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, Eq, PartialEq, Hash)]
#[serde(rename_all = "lowercase")]
pub enum LockAction {
    Add,
    Remove,
}

/// A change to be applied to `Locks`
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, Eq, PartialEq, Hash)]
pub struct LockChange {
    pub job_id: u64,
    pub content_type_id: u32,
    pub item_id: u32,
    pub description: String,
    pub lock_type: LockType,
    pub action: LockAction,
}

impl ToCompositeId for LockChange {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id, self.item_id)
    }
}

/// Meta is the metadata object returned by a fetch call
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct Meta {
    pub limit: u32,
    pub next: Option<u32>,
    pub offset: u32,
    pub previous: Option<u32>,
    pub total_count: u32,
}

/// ApiList contains the metadata and the `Vec` of objects returned by a fetch call
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct ApiList<T> {
    pub meta: Meta,
    pub objects: Vec<T>,
}

#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct ActionArgs {
    pub host_id: Option<u64>,
    pub target_id: Option<u64>,
}

// An available action from `/api/action/`
#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct AvailableAction {
    pub args: Option<ActionArgs>,
    pub composite_id: String,
    pub class_name: Option<String>,
    pub confirmation: Option<String>,
    pub display_group: u64,
    pub display_order: u64,
    pub long_description: String,
    pub state: Option<String>,
    pub verb: String,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct ClientMount {
    pub filesystem_name: String,
    pub mountpoint: Option<String>,
    pub state: String,
}

/// A Host record from `/api/host/`
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Host {
    pub address: String,
    pub boot_time: Option<String>,
    pub client_mounts: Option<Vec<ClientMount>>,
    pub content_type_id: u32,
    pub corosync_configuration: Option<String>,
    pub corosync_ring0: String,
    pub fqdn: String,
    pub id: u32,
    pub immutable_state: bool,
    pub install_method: String,
    pub label: String,
    pub lnet_configuration: String,
    pub member_of_active_filesystem: bool,
    pub needs_update: bool,
    pub nids: Option<Vec<String>>,
    pub nodename: String,
    pub pacemaker_configuration: Option<String>,
    pub private_key: Option<String>,
    pub private_key_passphrase: Option<String>,
    pub properties: String,
    pub resource_uri: String,
    pub root_pw: Option<String>,
    pub server_profile: ServerProfile,
    pub state: String,
    pub state_modified_at: String,
}

impl ToCompositeId for Host {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id, self.id)
    }
}

impl Label for Host {
    fn label(&self) -> &str {
        &self.label
    }
}

impl EndpointName for Host {
    fn endpoint_name() -> &'static str {
        "host"
    }
}

/// A server profile record from api/server_profile/
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct ServerProfile {
    pub corosync: bool,
    pub corosync2: bool,
    pub default: bool,
    pub initial_state: String,
    pub managed: bool,
    pub name: String,
    pub ntp: bool,
    pub pacemaker: bool,
    pub repolist: Vec<String>,
    pub resource_uri: String,
    pub ui_description: String,
    pub ui_name: String,
    pub user_selectable: bool,
    pub worker: bool,
}

impl EndpointName for ServerProfile {
    fn endpoint_name() -> &'static str {
        "server_profile"
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Command {
    pub cancelled: bool,
    pub complete: bool,
    pub created_at: String,
    pub errored: bool,
    pub id: u32,
    pub jobs: Vec<String>,
    pub logs: String,
    pub message: String,
    pub resource_uri: String,
}

impl EndpointName for Command {
    fn endpoint_name() -> &'static str {
        "command"
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
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

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct OstConfParams {
    #[serde(rename = "osc.active")]
    osc_active: Option<String>,
    #[serde(rename = "osc.max_dirty_mb")]
    osc_max_dirty_mb: Option<String>,
    #[serde(rename = "osc.max_pages_per_rpc")]
    osc_max_pages_per_rpc: Option<String>,
    #[serde(rename = "osc.max_rpcs_in_flight")]
    osc_max_rpcs_in_flight: Option<String>,
    #[serde(rename = "ost.OSS.ost.threads_max")]
    ost_oss_ost_threads_max: Option<String>,
    #[serde(rename = "ost.OSS.ost.threads_min")]
    ost_oss_ost_threads_min: Option<String>,
    #[serde(rename = "ost.OSS.ost_create.threads_max")]
    ost_oss_ost_create_threads_max: Option<String>,
    #[serde(rename = "ost.OSS.ost_create.threads_min")]
    ost_oss_ost_create_threads_min: Option<String>,
    #[serde(rename = "ost.OSS.ost_io.threads_max")]
    ost_oss_ost_io_threads_max: Option<String>,
    #[serde(rename = "ost.OSS.ost_io.threads_min")]
    ost_oss_ost_io_threads_min: Option<String>,
    #[serde(rename = "ost.read_cache_enable")]
    ost_read_cache_enable: Option<String>,
    #[serde(rename = "ost.readcache_max_filesize")]
    ost_readcache_max_filesize: Option<String>,
    #[serde(rename = "ost.sync_journal")]
    ost_sync_journal: Option<String>,
    #[serde(rename = "ost.sync_on_lock_cancel")]
    ost_sync_on_lock_cancel: Option<String>,
    #[serde(rename = "ost.writethrough_cache_enable")]
    ost_writethrough_cache_enable: Option<String>,
}

/// A Volume record from api/volume/
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Volume {
    pub filesystem_type: Option<String>,
    pub id: u32,
    pub kind: String,
    pub label: String,
    pub resource_uri: String,
    pub size: Option<String>,
    pub status: Option<String>,
    pub storage_resource: Option<String>,
    pub usable_for_lustre: bool,
    pub volume_nodes: Vec<VolumeNode>,
}

impl Label for Volume {
    fn label(&self) -> &str {
        &self.label
    }
}

impl EndpointName for Volume {
    fn endpoint_name() -> &'static str {
        "volume"
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct VolumeNode {
    pub host: String,
    pub host_id: u32,
    pub host_label: String,
    pub id: u32,
    pub path: String,
    pub primary: bool,
    pub resource_uri: String,
    #[serde(rename = "use")]
    pub _use: bool,
    pub volume_id: u32,
}

impl EndpointName for VolumeNode {
    fn endpoint_name() -> &'static str {
        "volume_node"
    }
}

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
#[serde(untagged)]
pub enum TargetConfParam {
    MdtConfParam(MdtConfParams),
    OstConfParam(OstConfParams),
}

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
#[serde(untagged)]
pub enum VolumeOrResourceUri {
    ResourceUri(String),
    Volume(Volume),
}

/// A Target record from /api/target/
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct Target<T> {
    pub active_host: Option<String>,
    pub active_host_name: String,
    pub conf_params: Option<T>,
    pub content_type_id: u32,
    pub failover_server_name: String,
    pub failover_servers: Vec<String>,
    pub filesystem: Option<String>,
    pub filesystem_id: Option<u32>,
    pub filesystem_name: Option<String>,
    pub filesystems: Option<Vec<FilesystemShort>>,
    pub ha_label: Option<String>,
    pub id: u32,
    pub immutable_state: bool,
    pub index: Option<u32>,
    pub inode_count: Option<String>,
    pub inode_size: Option<u32>,
    pub kind: String,
    pub label: String,
    pub name: String,
    pub primary_server: String,
    pub primary_server_name: String,
    pub resource_uri: String,
    pub state: String,
    pub state_modified_at: String,
    pub uuid: Option<String>,
    pub volume: VolumeOrResourceUri,
    pub volume_name: String,
}

impl<T> ToCompositeId for Target<T> {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id, self.id)
    }
}

impl<T> Label for Target<T> {
    fn label(&self) -> &str {
        &self.label
    }
}

impl<T> EndpointName for Target<T> {
    fn endpoint_name() -> &'static str {
        "target"
    }
}

type Mdt = Target<MdtConfParams>;

#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct HsmControlParamMdt {
    pub id: String,
    pub kind: String,
    pub resource: String,
    pub conf_params: MdtConfParams,
}

/// HsmControlParams used for hsm actions
#[derive(serde::Deserialize, serde::Serialize, PartialEq, Clone, Debug)]
pub struct HsmControlParam {
    pub long_description: String,
    pub param_key: String,
    pub param_value: String,
    pub verb: String,
    pub mdt: HsmControlParamMdt,
}

/// A Filesystem record from /api/filesystem/
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Filesystem {
    pub bytes_free: Option<f64>,
    pub bytes_total: Option<f64>,
    pub cdt_mdt: Option<String>,
    pub cdt_status: Option<String>,
    pub client_count: Option<f64>,
    pub conf_params: FilesystemConfParams,
    pub content_type_id: u32,
    pub files_free: Option<f64>,
    pub files_total: Option<f64>,
    pub hsm_control_params: Vec<HsmControlParam>,
    pub id: u32,
    pub immutable_state: bool,
    pub label: String,
    pub mdts: Vec<Mdt>,
    pub mgt: String,
    pub mount_command: String,
    pub mount_path: String,
    pub name: String,
    pub osts: Vec<String>,
    pub resource_uri: String,
    pub state: String,
    pub state_modified_at: String,
}

impl ToCompositeId for Filesystem {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id, self.id)
    }
}

impl Label for Filesystem {
    fn label(&self) -> &str {
        &self.label
    }
}

impl EndpointName for Filesystem {
    fn endpoint_name() -> &'static str {
        "filesystem"
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct FilesystemShort {
    pub id: u32,
    pub name: String,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub enum AlertType {
    AlertState,
    LearnEvent,
    AlertEvent,
    SyslogEvent,
    ClientConnectEvent,
    CommandRunningAlert,
    CommandSuccessfulAlert,
    CommandCancelledAlert,
    CommandErroredAlert,
    CorosyncUnknownPeersAlert,
    CorosyncToManyPeersAlert,
    CorosyncNoPeersAlert,
    CorosyncStoppedAlert,
    StonithNotEnabledAlert,
    PacemakerStoppedAlert,
    HostContactAlert,
    HostOfflineAlert,
    HostRebootEvent,
    UpdatesAvailableAlert,
    TargetOfflineAlert,
    TargetFailoverAlert,
    TargetRecoveryAlert,
    StorageResourceOffline,
    StorageResourceAlert,
    StorageResourceLearnEvent,
    PowerControlDeviceUnavailableAlert,
    IpmiBmcUnavailableAlert,
    LNetOfflineAlert,
    LNetNidsChangedAlert,
    StratagemUnconfiguredAlert,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub enum AlertSeverity {
    INFO,
    DEBUG,
    CRITICAL,
    WARNING,
    ERROR,
}

/// An Alert record from /api/alert/
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Alert {
    pub _message: Option<String>,
    pub active: Option<bool>,
    pub affected: Option<Vec<String>>,
    pub alert_item: String,
    pub alert_item_id: Option<i32>,
    pub alert_item_str: String,
    pub alert_type: String,
    pub begin: String,
    pub dismissed: bool,
    pub end: Option<String>,
    pub id: u32,
    pub lustre_pid: Option<i32>,
    pub message: String,
    pub record_type: AlertType,
    pub resource_uri: String,
    pub severity: AlertSeverity,
    pub variant: String,
}

impl EndpointName for Alert {
    fn endpoint_name() -> &'static str {
        "alert"
    }
}
