// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::Result,
    daemon_plugins::{DaemonBox, OutputValue},
};
use futures::{Future, TryFutureExt};
use iml_wire_types::{AgentResult, Id, PluginName, Seq};
use parking_lot::{Mutex, RwLock, RwLockReadGuard, RwLockWriteGuard};
use std::{
    collections::HashMap,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio_timer::clock;
use tracing::{info, warn};

/// Takes a `Duration` and figures out the next duration
/// for a bounded linear backoff.
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

        std::mem::replace(self, State::Empty(clock::now()));

        Ok(())
    }
    pub fn reset_active(&mut self) {
        if let State::Active(a) = self {
            a.instant = clock::now() + Duration::from_secs(10);
        }
    }
    pub fn reset_empty(&mut self) {
        std::mem::replace(self, State::Empty(clock::now() + Duration::from_secs(10)));
    }
    pub fn convert_to_pending(&mut self) {
        if let State::Empty(_) = self {
            std::mem::replace(self, State::Pending);
        } else {
            warn!("Session was not in Empty state");
        }
    }
}

#[derive(Clone)]
pub struct Sessions(Arc<RwLock<HashMap<PluginName, State>>>);

impl Sessions {
    pub fn new(plugins: &[PluginName]) -> Self {
        let hm = plugins
            .iter()
            .cloned()
            .map(|x| (x, State::Empty(clock::now())))
            .collect();

        Self(Arc::new(RwLock::new(hm)))
    }
    pub fn reset_active(&mut self, name: &PluginName) {
        if let Some(x) = self.0.write().get_mut(name) {
            x.reset_active()
        }
    }
    pub fn reset_empty(&mut self, name: &PluginName) {
        if let Some(x) = self.0.write().get_mut(name) {
            x.reset_empty()
        }
    }
    pub fn convert_to_pending(&mut self, name: &PluginName) {
        if let Some(x) = self.0.write().get_mut(name) {
            x.convert_to_pending()
        }
    }
    pub fn insert_session(&mut self, name: PluginName, s: Session) {
        self.0.write().insert(
            name,
            State::Active(Active {
                session: s,
                instant: clock::now() + Duration::from_secs(10),
            }),
        );
    }
    pub fn message(
        &self,
        name: &PluginName,
        body: serde_json::Value,
    ) -> Option<impl Future<Output = Result<(SessionInfo, AgentResult)>>> {
        if let Some(State::Active(active)) = self.0.read().get(name) {
            Some(active.session.message(body))
        } else {
            warn!("Received a message for unknown session {}", name);

            None
        }
    }
    pub fn terminate_session(&mut self, name: &PluginName) -> Result<()> {
        match self.0.write().get_mut(name) {
            Some(s) => {
                s.teardown()?;
            }
            None => {
                warn!("Plugin {:?} not found in sessions", name);
            }
        };

        Ok(())
    }
    /// Terminates all held sessions.
    pub fn terminate_all_sessions(&mut self) -> Result<()> {
        info!("Terminating all sessions");

        self.0
            .write()
            .iter_mut()
            .map(|(_, v)| v.teardown())
            .collect::<Result<Vec<()>>>()
            .map(|_| ())
    }
    pub fn write(&mut self) -> RwLockWriteGuard<'_, HashMap<PluginName, State>> {
        self.0.write()
    }
    pub fn read(&mut self) -> RwLockReadGuard<'_, HashMap<PluginName, State>> {
        self.0.read()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SessionInfo {
    pub name: PluginName,
    pub id: Id,
    pub seq: Seq,
}

fn addon_info<T>(info: &mut SessionInfo, output: T) -> (SessionInfo, T) {
    info.seq.increment();

    (info.clone(), output)
}

#[derive(Debug)]
pub struct Session {
    pub info: Arc<Mutex<SessionInfo>>,
    plugin: DaemonBox,
}

impl Session {
    pub fn new(name: PluginName, id: Id, plugin: DaemonBox) -> Self {
        info!("Created new session {:?}/{:?}", name, id);

        Self {
            info: Arc::new(Mutex::new(SessionInfo {
                name,
                id,
                seq: Seq::default(),
            })),
            plugin,
        }
    }
    pub fn start(&mut self) -> impl Future<Output = Result<Option<(SessionInfo, OutputValue)>>> {
        let info = Arc::clone(&self.info);

        self.plugin
            .start_session()
            .map_ok(move |x| x.map(|y| addon_info(&mut info.lock(), y)))
    }
    pub fn poll(&self) -> impl Future<Output = Result<Option<(SessionInfo, OutputValue)>>> {
        let info = Arc::clone(&self.info);

        self.plugin
            .update_session()
            .map_ok(move |x| x.map(|y| addon_info(&mut info.lock(), y)))
    }
    pub fn message(
        &self,
        body: serde_json::Value,
    ) -> impl Future<Output = Result<(SessionInfo, AgentResult)>> {
        let info = Arc::clone(&self.info);

        self.plugin
            .on_message(body)
            .map_ok(move |x| addon_info(&mut info.lock(), x))
    }
    pub fn teardown(&mut self) -> Result<()> {
        let info = self.info.lock();

        info!("Terminating session {:?}/{:?}", info.name, info.id);

        self.plugin.teardown()
    }
}

#[cfg(test)]
mod tests {
    use super::{Session, SessionInfo, Sessions, State};
    use crate::{
        agent_error::Result, daemon_plugins::daemon_plugin::test_plugin::TestDaemonPlugin,
    };
    use serde_json::json;
    use tokio_timer::clock;

    fn create_session() -> Session {
        Session::new(
            "test_plugin".into(),
            "1234".into(),
            Box::new(TestDaemonPlugin::default()),
        )
    }

    #[tokio::test]
    async fn test_session_start() -> Result<()> {
        let mut session = create_session();

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 1.into(),
        };

        let actual = session.start().await?;

        assert_eq!(actual, Some((session_info, json!(0))));

        Ok(())
    }

    #[tokio::test]
    async fn test_session_update() -> Result<()> {
        let mut session = create_session();

        session.start().await?;

        let actual = session.poll().await?;

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 2.into(),
        };

        assert_eq!(actual, Some((session_info, json!(1))));

        Ok(())
    }

    #[tokio::test]
    async fn test_session_message() -> Result<()> {
        let mut session = create_session();

        session.start().await?;

        let actual = session.message(json!("hi!")).await?;

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 2.into(),
        };

        assert_eq!(actual, (session_info, Ok(json!("hi!"))));

        Ok(())
    }

    #[test]
    fn test_session_state_pending() -> Result<()> {
        let mut state = State::Empty(clock::now());

        state.convert_to_pending();

        match state {
            State::Pending => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }

    #[test]
    fn test_sessions_convert_to_pending() -> Result<()> {
        let mut sessions = Sessions::new(&["test_plugin".into()]);

        sessions.convert_to_pending(&"test_plugin".into());

        let sessions = sessions.read();

        let state = sessions.get(&"test_plugin".into()).unwrap();

        match state {
            State::Pending => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }

    #[test]
    fn test_sessions_insert_session() -> Result<()> {
        let mut sessions = Sessions::new(&["test_plugin".into()]);

        let session = create_session();

        sessions.insert_session("test_plugin".into(), session);

        let sessions = sessions.read();
        let state = sessions.get(&"test_plugin".into()).unwrap();

        match state {
            State::Active(_) => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }

    #[tokio::test]
    async fn test_sessions_session_message() -> Result<()> {
        let mut sessions = Sessions::new(&["test_plugin".into()]);

        let session = create_session();

        sessions.insert_session("test_plugin".into(), session);

        let fut = sessions
            .message(&"test_plugin".into(), json!("hi!"))
            .unwrap();

        let sessions = sessions.read();
        let state = sessions.get(&"test_plugin".into()).unwrap();

        let actual = fut.await?;

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 1.into(),
        };

        assert_eq!(actual, (session_info, Ok(json!("hi!"))));

        match state {
            State::Active(_) => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }
}
