// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{NoSessionError, Result},
    daemon_plugins::{DaemonBox, OutputValue},
};
use futures::{channel::oneshot, future, Future, future::Either};
use iml_wire_types::{AgentResult, Id, PluginName, Seq};
use std::{
    collections::HashMap,
    ops::Deref,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::{Mutex, RwLock};
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
    pub in_flight: Option<oneshot::Receiver<()>>,
    pub instant: Instant,
}

#[derive(Debug)]
pub enum State {
    Active(Active),
    Pending,
    Empty(Instant),
}

impl State {
    pub async fn teardown(&mut self) -> Result<()> {
        if let State::Active(a) = self {
            a.session.teardown().await?;
        }

        std::mem::replace(self, State::Empty(Instant::now()));

        Ok(())
    }
    pub fn reset_active(&mut self) {
        if let State::Active(a) = self {
            a.instant = Instant::now() + Duration::from_secs(10);
            a.in_flight = None;
        }
    }
    pub fn create_active(&mut self, session: Session, in_flight: oneshot::Receiver<()>) {
        std::mem::replace(
            self,
            State::Active(Active {
                session,
                in_flight: Some(in_flight),
                instant: Instant::now() + Duration::from_secs(10),
            }),
        );
    }
    pub fn reset_empty(&mut self) {
        std::mem::replace(self, State::Empty(Instant::now() + Duration::from_secs(10)));
    }
    pub fn convert_to_pending(&mut self) {
        if let State::Empty(_) = self {
            std::mem::replace(self, State::Pending);
        } else {
            warn!("Session was not in Empty state");
        }
    }
}

/// Holds all information about active sessions.
/// There is one important invariant: The inner `HashMap`
/// should never be mutated directly.
/// State changes are done via interior mutability.
#[derive(Clone)]
pub struct Sessions(pub Arc<HashMap<PluginName, Arc<RwLock<State>>>>);

impl Sessions {
    pub fn new(plugins: &[PluginName]) -> Self {
        let hm = plugins
            .iter()
            .cloned()
            .map(|x| (x, Arc::new(RwLock::new(State::Empty(Instant::now())))))
            .collect();

        Self(Arc::new(hm))
    }
    pub async fn reset_active(&self, name: &PluginName) {
        if let Some(x) = self.0.get(name) {
            x.write().await.reset_active()
        }
    }
    pub async fn reset_empty(&self, name: &PluginName) {
        if let Some(x) = self.0.get(name) {
            x.write().await.reset_empty()
        }
    }
    pub async fn convert_to_pending(&self, name: &PluginName) {
        if let Some(x) = self.0.get(name) {
            x.write().await.convert_to_pending()
        }
    }
    pub async fn insert_session(
        &self,
        name: PluginName,
        s: Session,
        in_flight: oneshot::Receiver<()>,
    ) -> Result<()> {
        let state = self
            .0
            .get(&name)
            .ok_or_else(|| NoSessionError(name))?
            .clone();

        state.write().await.create_active(s, in_flight);

        Ok(())
    }
    pub async fn message(
        &self,
        name: &PluginName,
        body: serde_json::Value,
    ) -> Option<Result<(SessionInfo, AgentResult)>> {
        let state = self.0.get(name).or_else(|| {
            warn!("Received a message for unknown session {}", name);
            None
        })?;

        if let State::Active(active) = state.read().await.deref() {
            Some(active.session.message(body).await)
        } else {
            warn!(
                "Received a message for session in non-active state {}",
                name
            );

            None
        }
    }

    pub async fn terminate_session(&self, name: &PluginName) -> Result<()> {
        match self.0.get(name) {
            Some(s) => {
                s.write().await.teardown().await?;
            }
            None => {
                warn!("Plugin {:?} not found in sessions", name);
            }
        };

        Ok(())
    }
    /// Terminates all held sessions.
    pub async fn terminate_all_sessions(&self) -> Result<()> {
        info!("Terminating all sessions");

        let xs = self
            .0
            .values()
            .map(|x| async move { x.write().await.teardown().await })
            .collect::<Vec<_>>();

        future::try_join_all(xs).await.map(drop)
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
    pub fn start(
        &mut self,
    ) -> (
        oneshot::Receiver<()>,
        impl Future<Output = Result<Option<(SessionInfo, OutputValue)>>>,
    ) {
        let info = Arc::clone(&self.info);

        let (mut tx, rx) = oneshot::channel();

        let fut = self.plugin.start_session();

        let fut = async move {
            let either = future::select(tx.cancellation(), fut).await;

            match either {
                Either::Left(_) => {
                    let info = info.lock().await;

                    tracing::warn!(
                        "Session start for {}/{} has been cancelled. Will try again",
                        info.name,
                        info.id
                    );

                    Ok(None)
                }
                Either::Right((Ok(Some(x)), _)) => {
                    let mut info = info.lock().await;

                    Ok(Some(addon_info(&mut info, x)))
                }
                Either::Right((Ok(None), _)) => Ok(None),
                Either::Right((Err(e), _)) => Err(e),
            }
        };

        (rx, fut)
    }
    pub fn poll(
        &self,
    ) -> (
        oneshot::Receiver<()>,
        impl Future<Output = Result<Option<(SessionInfo, OutputValue)>>>,
    ) {
        let info = Arc::clone(&self.info);

        let (mut tx, rx) = oneshot::channel();

        let fut = self.plugin.update_session();

        let fut = async move {
            let either = future::select(tx.cancellation(), fut).await;

            match either {
                Either::Left(_) => {
                    let info = info.lock().await;

                    tracing::warn!(
                        "Session poll for {}/{} has been cancelled. Will try again",
                        info.name,
                        info.id
                    );

                    Ok(None)
                }
                Either::Right((Ok(Some(x)), _)) => {
                    let mut info = info.lock().await;

                    Ok(Some(addon_info(&mut info, x)))
                }
                Either::Right((Ok(None), _)) => Ok(None),
                Either::Right((Err(e), _)) => Err(e),
            }
        };

        (rx, fut)
    }
    pub async fn message(&self, body: serde_json::Value) -> Result<(SessionInfo, AgentResult)> {
        let info = Arc::clone(&self.info);

        let x = self.plugin.on_message(body).await?;

        let mut info = info.lock().await;

        Ok(addon_info(&mut info, x))
    }
    pub async fn teardown(&mut self) -> Result<()> {
        let info = self.info.lock().await;

        info!("Terminating session {:?}/{:?}", info.name, info.id);

        self.plugin.teardown().await
    }
}

#[cfg(test)]
mod tests {
    use super::{Session, SessionInfo, Sessions, State};
    use crate::{
        agent_error::Result, daemon_plugins::daemon_plugin::test_plugin::TestDaemonPlugin,
    };
    use futures::channel::oneshot;
    use serde_json::json;
    use std::{ops::Deref, time::Instant};

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

        let (_rx, fut) = session.start();

        let actual = fut.await?;

        assert_eq!(actual, Some((session_info, json!(0))));

        Ok(())
    }

    #[tokio::test(core_threads = 2)]
    async fn test_session_start_cancel() -> Result<()> {
        let mut session = create_session();

        let (rx, fut) = session.start();

        drop(rx);

        let actual = fut.await?;

        assert_eq!(actual, None);

        Ok(())
    }

    #[tokio::test]
    async fn test_session_update() -> Result<()> {
        let mut session = create_session();

        let (_rx, fut) = session.start();

        fut.await?;

        let (_rx, fut) = session.poll();

        let actual = fut.await?;

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 2.into(),
        };

        assert_eq!(actual, Some((session_info, json!(1))));

        Ok(())
    }

    #[tokio::test]
    async fn test_session_update_cancel() -> Result<()> {
        let mut session = create_session();

        let (_rx, fut) = session.start();

        fut.await?;

        let (rx, fut) = session.poll();

        drop(rx);

        let actual = fut.await?;

        assert_eq!(actual, None);

        Ok(())
    }

    #[tokio::test]
    async fn test_session_message() -> Result<()> {
        let mut session = create_session();

        let (_rx, fut) = session.start();

        fut.await?;

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
        let mut state = State::Empty(Instant::now());

        state.convert_to_pending();

        match state {
            State::Pending => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }

    #[tokio::test]
    async fn test_sessions_convert_to_pending() -> Result<()> {
        let sessions = Sessions::new(&["test_plugin".into()]);

        sessions.convert_to_pending(&"test_plugin".into()).await;

        let state = sessions.0.get(&"test_plugin".into()).cloned().unwrap();
        let state = state.read().await;

        match state.deref() {
            State::Pending => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }

    #[tokio::test]
    async fn test_sessions_insert_session() -> Result<()> {
        let sessions = Sessions::new(&["test_plugin".into()]);

        let session = create_session();

        let (_tx, rx) = oneshot::channel();

        sessions
            .insert_session("test_plugin".into(), session, rx)
            .await?;

        let state = sessions.0.get(&"test_plugin".into()).cloned().unwrap();
        let state = state.read().await;

        match state.deref() {
            State::Active(_) => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }

    #[tokio::test]
    async fn test_sessions_session_message() -> Result<()> {
        let sessions = Sessions::new(&["test_plugin".into()]);

        let session = create_session();

        let (_tx, rx) = oneshot::channel();

        sessions
            .insert_session("test_plugin".into(), session, rx)
            .await?;

        let plugin_name = "test_plugin".into();

        let fut = sessions.message(&plugin_name, json!("hi!"));

        let state = sessions.0.get(&"test_plugin".into()).cloned().unwrap();
        let state = state.read().await;

        let actual = fut.await.unwrap()?;

        let session_info = SessionInfo {
            name: "test_plugin".into(),
            id: "1234".into(),
            seq: 1.into(),
        };

        assert_eq!(actual, (session_info, Ok(json!("hi!"))));

        match state.deref() {
            State::Active(_) => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }
}
