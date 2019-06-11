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
    host_id: Option<u64>,
    target_id: Option<u64>,
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

/// A Host record from `/api/host/`
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Host {
    pub address: String,
    pub boot_time: String,
    pub client_mounts: Vec<String>,
    pub content_type_id: u64,
    pub corosync_configuration: String,
    pub corosync_ring0: String,
    pub fqdn: String,
    pub id: u64,
    pub immutable_state: bool,
    pub install_method: String,
    pub label: String,
    pub lnet_configuration: String,
    pub member_of_active_filesystem: bool,
    pub needs_update: bool,
    pub nids: Vec<String>,
    pub nodename: String,
    pub pacemaker_configuration: String,
    pub private_key: Option<String>,
    pub private_key_passphrase: Option<String>,
    pub properties: String,
    pub resource_uri: String,
    pub root_pw: Option<String>,
    pub server_profile: ServerProfile,
    pub state: String,
    pub state_modified_at: String,
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

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct Command {
    pub cancelled: bool,
    pub complete: bool,
    pub created_at: String,
    pub errored: bool,
    pub id: u64,
    pub jobs: Vec<String>,
    pub logs: String,
    pub message: String,
    pub resource_uri: String,
}
