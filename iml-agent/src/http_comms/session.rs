// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{NoSessionError, Result},
    daemon_plugins::{DaemonBox, Output, OutputValue},
};
use futures::{channel::oneshot, future, future::Either, lock::Mutex, Future};
use iml_wire_types::{AgentResult, Id, PluginName};
use std::sync::atomic::{AtomicU64, Ordering};
use std::{
    collections::HashMap,
    ops::Deref,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::RwLock;
use tracing::{info, warn};

const WAIT_TIME: Duration = Duration::from_secs(5);

/// Takes a `Duration` and figures out the next duration
/// for a bounded linear backoff.
///
/// # Arguments
///
/// * `d` - The `Duration` used to calculate the next `Duration`
pub fn backoff_schedule(d: Duration) -> Duration {
    match d.as_secs() {
        0 | 1 => WAIT_TIME,
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
    pub fn is_active(&self, id: &Id) -> bool {
        match self {
            State::Active(ref a) => &a.session.id == id,
            _ => false,
        }
    }
    pub async fn teardown(&mut self) -> Result<()> {
        if let State::Active(a) = self {
            a.session.teardown().await?;
        }

        let _ = std::mem::replace(self, State::Empty(Instant::now()));

        Ok(())
    }
    pub fn reset_active(&mut self) {
        if let State::Active(a) = self {
            a.instant = Instant::now() + WAIT_TIME;
            a.in_flight = None;
        }
    }
    pub fn create_active(&mut self, session: Session, in_flight: oneshot::Receiver<()>) {
        let _ = std::mem::replace(
            self,
            State::Active(Active {
                session,
                in_flight: Some(in_flight),
                instant: Instant::now() + WAIT_TIME,
            }),
        );
    }
    pub fn reset_empty(&mut self) {
        let _ = std::mem::replace(self, State::Empty(Instant::now() + WAIT_TIME));
    }
    pub fn convert_to_pending(&mut self) {
        if let State::Empty(_) = self {
            let _ = std::mem::replace(self, State::Pending);
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
            x.write().await.reset_active();

            tracing::trace!("Reset active for {:?}", name);
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
    ) -> Option<Result<(u64, PluginName, Id, AgentResult)>> {
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

    pub async fn terminate_session(&self, name: &PluginName, id: &Id) -> Result<()> {
        match self.0.get(name) {
            Some(s) => {
                let is_active = { s.read().await.is_active(id) };

                if !is_active {
                    tracing::warn!("Did not find active session for {}/{}", name, id);
                    return Ok(());
                }

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

#[derive(Debug)]
pub struct Session {
    pub info: Arc<AtomicU64>,
    pub name: PluginName,
    pub id: Id,
    /// The state from the last `update_session` call.
    pub last_update: Arc<Mutex<Output>>,
    plugin: DaemonBox,
}

impl Session {
    pub fn new(name: PluginName, id: Id, plugin: DaemonBox) -> Self {
        info!("Created new session {:?}/{:?}", name, id);

        Self {
            name,
            id,
            info: Arc::new(AtomicU64::new(0)),
            last_update: Arc::new(Mutex::new(None)),
            plugin,
        }
    }
    /// Get the deadline of the inner plugin
    pub fn deadline(&self) -> std::time::Duration {
        self.plugin.deadline()
    }
    pub fn start(
        &mut self,
    ) -> (
        oneshot::Receiver<()>,
        impl Future<Output = Result<Option<(u64, PluginName, Id, OutputValue)>>>,
    ) {
        let info = Arc::clone(&self.info);

        let (mut tx, rx) = oneshot::channel();

        let fut = self.plugin.start_session();

        let name = self.name.clone();
        let id = self.id.clone();

        let fut = async move {
            let either = future::select(tx.cancellation(), fut).await;

            match either {
                Either::Left(_) => {
                    tracing::warn!(
                        "Session start for {}/{} has been cancelled. Will try again",
                        name,
                        id
                    );

                    Ok(None)
                }
                Either::Right((Ok(Some(x)), _)) => {
                    info.fetch_add(1, Ordering::SeqCst);
                    let seq = info.load(Ordering::SeqCst);

                    Ok(Some((seq, name, id, x)))
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
        impl Future<Output = Result<Option<(u64, PluginName, Id, OutputValue)>>>,
    ) {
        let info = Arc::clone(&self.info);

        let last_update = Arc::clone(&self.last_update);

        let (mut tx, rx) = oneshot::channel();

        let fut = self.plugin.update_session();

        let name = self.name.clone();
        let id = self.id.clone();

        let fut = async move {
            let either = future::select(tx.cancellation(), fut).await;

            match either {
                Either::Left(_) => {
                    tracing::warn!(
                        "Session poll for {}/{} has been cancelled. Will try again",
                        name,
                        id
                    );

                    Ok(None)
                }
                Either::Right((Ok(Some(x)), _)) => {
                    let mut last_update = last_update.lock().await;

                    if last_update.deref().as_ref() == Some(&x) {
                        return Ok(None);
                    }

                    last_update.replace(x.clone());

                    info.fetch_add(1, Ordering::SeqCst);
                    let seq = info.load(Ordering::SeqCst);

                    Ok(Some((seq, name, id, x)))
                }
                Either::Right((Ok(None), _)) => Ok(None),
                Either::Right((Err(e), _)) => Err(e),
            }
        };

        (rx, fut)
    }
    pub async fn message(
        &self,
        body: serde_json::Value,
    ) -> Result<(u64, PluginName, Id, AgentResult)> {
        let info = Arc::clone(&self.info);

        let name = self.name.clone();
        let id = self.id.clone();

        let x = self.plugin.on_message(body).await?;

        info.fetch_add(1, Ordering::SeqCst);
        let seq = info.load(Ordering::SeqCst);

        Ok((seq, name, id, x))
    }
    pub async fn teardown(&mut self) -> Result<()> {
        info!("Terminating session {:?}/{:?}", self.name, self.id);

        self.plugin.teardown().await
    }
}

#[cfg(test)]
mod tests {
    use super::{Session, Sessions, State};
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

        let (_rx, fut) = session.start();

        let actual = fut.await?;

        assert_eq!(
            actual,
            Some((1, "test_plugin".into(), "1234".into(), json!(0)))
        );

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

        assert_eq!(
            actual,
            Some((2, "test_plugin".into(), "1234".into(), json!(1)))
        );

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

        assert_eq!(
            actual,
            (2, "test_plugin".into(), "1234".into(), Ok(json!("hi!")))
        );

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

        assert_eq!(
            actual,
            (1, "test_plugin".into(), "1234".into(), Ok(json!("hi!")))
        );

        match state.deref() {
            State::Active(_) => Ok(()),
            _ => panic!("State was not Pending"),
        }
    }
}
