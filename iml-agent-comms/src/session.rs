// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::{Fqdn, Id, ManagerMessage, PluginName};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};
use uuid::Uuid;

pub type Sessions = Arc<Mutex<InnerSessions>>;

pub type InnerSessions = HashMap<PluginName, Session>;

/// A bidirectional virtual channel between the manager and a remote agent plugin.
/// There may be many of these per remote host, and they are transient.
#[derive(Clone, Debug)]
pub struct Session {
    pub fqdn: Fqdn,
    pub id: Id,
    pub plugin: PluginName,
}

impl std::fmt::Display for Session {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{:?}/{:?}/{:?}", self.fqdn, self.plugin, self.id,)
    }
}

impl Session {
    pub fn new(plugin: PluginName, fqdn: Fqdn) -> Self {
        Session {
            fqdn,
            id: Id(Uuid::new_v4().to_hyphenated().to_string()),
            plugin,
        }
    }
}

pub fn is_session_valid(msg: &ManagerMessage, sessions: &InnerSessions) -> bool {
    let retain = match msg {
        ManagerMessage::SessionTerminateAll { .. } => true,
        ManagerMessage::SessionTerminate {
            session_id, plugin, ..
        }
        | ManagerMessage::SessionCreateResponse {
            session_id, plugin, ..
        }
        | ManagerMessage::Data {
            session_id, plugin, ..
        } => sessions
            .get(&plugin)
            .filter(|Session { id, .. }| id == session_id)
            .is_some(),
    };

    if !retain {
        log::info!(
            "Dropping message {:?} because it does not match any held session. Sessions: {:?}",
            msg,
            sessions
        );
    }

    retain
}
