// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::{Fqdn, Id, ManagerMessage, PluginName};
use futures::lock::Mutex;
use std::{collections::HashMap, sync::Arc};
use uuid::Uuid;

pub type Shared<T> = Arc<Mutex<T>>;
pub type Sessions = HashMap<PluginName, Session>;
pub type SharedSessions = Shared<Sessions>;

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
        Self {
            fqdn,
            id: Id(Uuid::new_v4().to_hyphenated().to_string()),
            plugin,
        }
    }
}

pub fn get_by_session_id<'a>(
    plugin: &PluginName,
    id: &Id,
    sessions: &'a Sessions,
) -> Option<&'a Session> {
    sessions.get(plugin).filter(|s| &s.id == id)
}

pub fn is_session_valid(msg: &ManagerMessage, sessions: &Sessions) -> bool {
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
        } => get_by_session_id(&plugin, &session_id, sessions).is_some(),
    };

    if !retain {
        tracing::info!(
            "Dropping message {:?} because it does not match any held session. Sessions: {:?}",
            msg,
            sessions
        );
    }

    retain
}
