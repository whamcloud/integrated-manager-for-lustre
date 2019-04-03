// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{ImlAgentError, Result},
    daemon_plugins::{DaemonBox, OutputValue},
};
use futures::Future;
use iml_wire_types::{AgentResult, Id, PluginName, Seq};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};

/// Takes a `Duration` and figures out the next duration
/// for a bounded linear backoff.Duration
///
/// # Arguments
///
/// * `d` - The `Duration` used to calculate the next `Duration`
pub fn backoff_schedule(d: Duration) -> Duration {
    match d.as_secs() {
        0 | 1 => Duration::from_secs(10),
        r => Duration::from_secs(std::cmp::min(r * 2, 60)),
    }
}

#[derive(Debug)]
pub struct Active {
    pub session: Session,
    pub instant: Instant,
}

#[derive(Debug)]
pub enum State {
    Active(Active),
    Pending,
    Empty(Instant),
}

impl State {
    pub fn teardown(&mut self) -> Result<()> {
        if let State::Active(a) = self {
            a.session.teardown()?;
        }

        std::mem::replace(self, State::Empty(Instant::now()));

        Ok(())
    }
    pub fn reset_active(&mut self) {
        if let State::Active(a) = self {
            a.instant = Instant::now() + Duration::from_secs(10);
        }
    }
    pub fn reset_empty(&mut self) {
        if let State::Empty(_) = self {
            std::mem::replace(self, State::Empty(Instant::now() + Duration::from_secs(10)));
        }
    }
    pub fn convert_to_pending(&mut self) {
        std::mem::replace(self, State::Pending);
    }
}

#[derive(Clone)]
pub struct Sessions(Arc<Mutex<HashMap<PluginName, State>>>);

impl Sessions {
    pub fn new(plugins: &[PluginName]) -> Sessions {
        let hm = plugins
            .iter()
            .cloned()
            .map(|x| (x, State::Empty(Instant::now())))
            .collect();

        Sessions(Arc::new(Mutex::new(hm)))
    }
    pub fn reset_active(&mut self, name: &PluginName) -> Result<()> {
        if let Some(x) = self.lock()?.get_mut(name) {
            x.reset_active()
        }

        Ok(())
    }
    pub fn reset_empty(&mut self, name: &PluginName) -> Result<()> {
        if let Some(x) = self.lock()?.get_mut(name) {
            x.reset_empty()
        }

        Ok(())
    }

    pub fn convert_to_pending(&mut self, name: &PluginName) -> Result<()> {
        if let Some(s @ State::Empty(_)) = self.lock()?.get_mut(name) {
            s.convert_to_pending()
        } else {
            log::warn!("Session {:?} was not in Empty state", name);
        }

        Ok(())
    }
    pub fn insert_session(&mut self, name: PluginName, s: Session) -> Result<()> {
        self.insert_state(
            name,
            State::Active(Active {
                session: s,
                instant: Instant::now() + Duration::from_secs(10),
            }),
        )
    }
    fn insert_state(&mut self, name: PluginName, state: State) -> Result<()> {
        self.0.lock()?.insert(name, state);

        Ok(())
    }
    pub fn terminate_session(&mut self, name: &PluginName) -> Result<()> {
        match self.0.lock()?.get_mut(name) {
            Some(s) => {
                s.teardown()?;
            }
            None => {
                log::warn!("Plugin {:?} not found in sessions", name);
            }
        };

        Ok(())
    }
    /// Terminates all held sessions.
    pub fn terminate_all_sessions(&mut self) -> Result<()> {
        log::info!("Terminating all sessions");

        self.0
            .lock()?
            .iter_mut()
            .map(|(_, v)| v.teardown())
            .collect::<Result<Vec<()>>>()
            .map(|_| ())
    }
    pub fn lock(&mut self) -> Result<std::sync::MutexGuard<'_, HashMap<PluginName, State>>> {
        Ok(self.0.lock()?)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SessionInfo {
    pub name: PluginName,
    pub id: Id,
    pub seq: Seq,
}

#[derive(Debug)]
pub struct Session {
    pub info: SessionInfo,
    plugin: DaemonBox,
}

impl Session {
    pub fn new(name: PluginName, id: Id, plugin: DaemonBox) -> Self {
        log::info!("Created new session {:?}/{:?}", name, id);

        Session {
            info: SessionInfo {
                name,
                id,
                seq: Seq(1),
            },
            plugin,
        }
    }
    pub fn start(
        &mut self,
    ) -> Box<Future<Item = Option<(SessionInfo, OutputValue)>, Error = ImlAgentError> + Send> {
        let info = self.info.clone();

        Box::new(self.plugin.start_session().map(|x| match x {
            Some(x) => Some((info, x)),
            None => None,
        }))
    }
    pub fn poll(
        &mut self,
    ) -> Box<Future<Item = Option<(SessionInfo, OutputValue)>, Error = ImlAgentError> + Send> {
        self.info.seq += Seq(1);
        let info = self.info.clone();

        Box::new(self.plugin.update_session().map(|x| match x {
            Some(x) => Some((info, x)),
            None => None,
        }))
    }
    pub fn message(
        &mut self,
        body: serde_json::Value,
    ) -> Box<Future<Item = (SessionInfo, AgentResult), Error = ImlAgentError> + Send> {
        self.info.seq += Seq(1);
        let info = self.info.clone();

        Box::new(self.plugin.on_message(body).map(|x| (info, x)))
    }
    pub fn teardown(&mut self) -> Result<()> {
        log::info!(
            "Terminating session {:?}/{:?}",
            self.info.name,
            self.info.id
        );

        self.plugin.teardown()
    }
}
