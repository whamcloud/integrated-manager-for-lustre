// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde_json;
use std::fmt;

#[derive(Eq, PartialEq, Hash, Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct PluginName(pub String);

impl From<PluginName> for String {
    fn from(PluginName(s): PluginName) -> String {
        s
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
    fn from(Fqdn(s): Fqdn) -> String {
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

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct Seq(pub u64);

impl std::ops::AddAssign for Seq {
    fn add_assign(&mut self, Seq(y): Seq) {
        self.0 += y;
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
        Envelope {
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

#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct ActionId(pub String);

impl fmt::Display for ActionId {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Things we can do with actions
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
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
