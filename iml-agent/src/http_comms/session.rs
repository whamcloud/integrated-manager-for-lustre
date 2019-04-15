// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{ImlAgentError, Result},
    daemon_plugins::{DaemonBox, OutputValue},
};
use futures::Future;
use iml_wire_types::{AgentResult, Id, PluginName, Seq};
use parking_lot::{Mutex, MutexGuard};
use std::{
    collections::HashMap,
    sync::Arc,
    time::{Duration, Instant},
};

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

        std::mem::replace(self, State::Empty(Instant::now()));

        Ok(())
    }
    pub fn reset_active(&mut self) {
        if let State::Active(a) = self {
            a.instant = Instant::now() + Duration::from_secs(10);
        }
    }
    pub fn reset_empty(&mut self) {
        std::mem::replace(self, State::Empty(Instant::now() + Duration::from_secs(10)));
    }
    pub fn convert_to_pending(&mut self) {
        std::mem::replace(self, State::Pending);
    }
}

#[derive(Clone)]
pub struct Sessions(Arc<Mutex<HashMap<PluginName, State>>>);

impl Sessions {
    pub fn new(plugins: &[PluginName]) -> Self {
        let hm = plugins
            .iter()
            .cloned()
            .map(|x| (x, State::Empty(Instant::now())))
            .collect();

        Self(Arc::new(Mutex::new(hm)))
    }
    pub fn reset_active(&mut self, name: &PluginName) -> Result<()> {
        if let Some(x) = self.lock().get_mut(name) {
            x.reset_active()
        }

        Ok(())
    }
    pub fn reset_empty(&mut self, name: &PluginName) -> Result<()> {
        if let Some(x) = self.lock().get_mut(name) {
            x.reset_empty()
        }

        Ok(())
    }

    pub fn convert_to_pending(&mut self, name: &PluginName) -> Result<()> {
        if let Some(s @ State::Empty(_)) = self.lock().get_mut(name) {
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
        self.0.lock().insert(name, state);

        Ok(())
    }
    pub fn terminate_session(&mut self, name: &PluginName) -> Result<()> {
        match self.0.lock().get_mut(name) {
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
            .lock()
            .iter_mut()
            .map(|(_, v)| v.teardown())
            .collect::<Result<Vec<()>>>()
            .map(|_| ())
    }
    pub fn lock(&mut self) -> MutexGuard<'_, HashMap<PluginName, State>> {
        self.0.lock()
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
        log::info!("Created new session {:?}/{:?}", name, id);

        Self {
            info: Arc::new(Mutex::new(SessionInfo {
                name,
                id,
                seq: Seq::default(),
            })),
            plugin,
        }
    }
    pub fn start(
        &self,
    ) -> Box<Future<Item = Option<(SessionInfo, OutputValue)>, Error = ImlAgentError> + Send> {
        let info = Arc::clone(&self.info);

        Box::new(
            self.plugin
                .start_session()
                .map(move |x| x.map(|y| addon_info(&mut info.lock(), y))),
        )
    }
    pub fn poll(
        &self,
    ) -> Box<Future<Item = Option<(SessionInfo, OutputValue)>, Error = ImlAgentError> + Send> {
        let info = Arc::clone(&self.info);

        Box::new(
            self.plugin
                .update_session()
                .map(move |x| x.map(|y| addon_info(&mut info.lock(), y))),
        )
    }
    pub fn message(
        &self,
        body: serde_json::Value,
    ) -> Box<Future<Item = (SessionInfo, AgentResult), Error = ImlAgentError> + Send> {
        let info = Arc::clone(&self.info);

        Box::new(
            self.plugin
                .on_message(body)
                .map(move |x| addon_info(&mut info.lock(), x)),
        )
    }
    pub fn teardown(&mut self) -> Result<()> {
        let info = self.info.lock();

        log::info!("Terminating session {:?}/{:?}", info.name, info.id);

        self.plugin.teardown()
    }
}

#[cfg(test)]
mod tests {
    use super::{Session, SessionInfo, State};
    use crate::{
        agent_error::Result, daemon_plugins::daemon_plugin::test_plugin::TestDaemonPlugin,
    };
    use futures::Future;
    use serde_json::json;
    use std::time::Instant;

    fn run<R: Send + 'static, E: Send + 'static>(
        fut: impl Future<Item = R, Error = E> + Send + 'static,
    ) -> std::result::Result<R, E> {
        tokio::runtime::Runtime::new().unwrap().block_on_all(fut)
    }

    fn create_session() -> Session {
        Session::new(
            "test_plugin".into(),
            "1234".into(),
            Box::new(TestDaemonPlugin::default()),
        )
    }

    #[test]
    fn test_session_start() -> Result<()> {
        let session = create_session();

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 1.into(),
        };

        let actual = run(session.start())?;

        assert_eq!(actual, Some((session_info, json!(0))));

        Ok(())
    }

    #[test]
    fn test_session_update() -> Result<()> {
        let session = create_session();

        run(session.start())?;

        let actual = run(session.poll())?;

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 2.into(),
        };

        assert_eq!(actual, Some((session_info, json!(1))));

        Ok(())
    }

    #[test]
    fn test_session_message() -> Result<()> {
        let session = create_session();

        run(session.start())?;

        let actual = run(session.message(json!("hi!")))?;

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
        let mut state = State::Empty(Instant::now());

        state.convert_to_pending();

        match state {
            State::Pending => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }
}
