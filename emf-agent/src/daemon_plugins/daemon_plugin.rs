// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{NoPluginError, Result},
    daemon_plugins::{
        action_runner, corosync, device, journal, network, ntp, ostpool, postoffice, snapshot,
        stats,
    },
};
use async_trait::async_trait;
use dyn_clone::DynClone;
use emf_wire_types::{AgentResult, PluginName};
use futures::{future, Future, FutureExt};
use std::{collections::HashMap, pin::Pin, time::Duration};
use tracing::info;

pub type OutputValue = serde_json::Value;
pub type Output = Option<OutputValue>;

/// Plugin interface for extensible behavior
/// between the agent and manager.
///
/// Maintains internal state and sends and receives messages.
///
/// Implementors of this trait should add themselves
/// to the `plugin_registry` below.
#[async_trait]
pub trait DaemonPlugin: std::fmt::Debug + Send + Sync + DynClone {
    /// The amount of time this plugin can run in a poll before it
    /// is considered stale and must be rescheduled
    fn deadline(&self) -> Duration {
        Duration::from_secs(1)
    }
    /// Returns full listing of information upon session esablishment
    fn start_session(&mut self) -> Pin<Box<dyn Future<Output = Result<Output>> + Send>> {
        future::ok(None).boxed()
    }
    /// Return information needed to maintain a manager-agent session, i.e. what
    /// has changed since the start of the session or since the last update.
    ///
    /// If you need to refer to any data from the start_session call, you can
    /// store it as a property on this DaemonPlugin instance.
    ///
    /// This will never be called concurrently with respect to start_session, or
    /// before start_session.
    fn update_session(&self) -> Pin<Box<dyn Future<Output = Result<Output>> + Send>> {
        future::ok(None).boxed()
    }
    /// Handle a message sent from the manager (may be called concurrently with respect to
    /// start_session and update_session).
    async fn on_message(&self, _body: serde_json::Value) -> Result<AgentResult> {
        Ok(Ok(serde_json::Value::Null))
    }
    async fn teardown(&mut self) -> Result<()> {
        Ok(())
    }
}

pub type DaemonBox = Box<dyn DaemonPlugin + Send + Sync>;

type Callback = Box<dyn Fn() -> DaemonBox + Send + Sync>;

fn mk_callback<D>(f: fn() -> D) -> Callback
where
    D: DaemonPlugin + Send + Sync + 'static,
{
    Box::new(move || Box::new(f()) as DaemonBox)
}

pub type DaemonPlugins = HashMap<PluginName, Callback>;

/// Returns a `HashMap` of plugins available for usage.
pub fn plugin_registry() -> DaemonPlugins {
    let hm: DaemonPlugins = vec![
        ("action_runner".into(), mk_callback(action_runner::create)),
        ("ntp".into(), mk_callback(ntp::create)),
        ("ostpool".into(), mk_callback(ostpool::create)),
        ("postoffice".into(), mk_callback(postoffice::create)),
        ("stats".into(), mk_callback(stats::create)),
        ("device".into(), mk_callback(device::create)),
        ("journal".into(), mk_callback(journal::create)),
        ("corosync".into(), mk_callback(corosync::create)),
        ("snapshot".into(), mk_callback(snapshot::create)),
        ("network".into(), mk_callback(network::create)),
    ]
    .into_iter()
    .collect();

    info!("Loaded the following DaemonPlugins:");

    for PluginName(key) in hm.keys() {
        info!("{}", key)
    }

    hm
}

/// Get a plugin instance, if it exists
///
/// # Arguments
///
/// * `name` - The plugin to instantiate
/// * `registry` - Plugin registry to use
pub fn get_plugin(name: &PluginName, registry: &DaemonPlugins) -> Result<DaemonBox> {
    match registry.get(name) {
        Some(f) => Ok(f()),
        None => Err(NoPluginError(name.clone()).into()),
    }
}

#[cfg(test)]
pub mod test_plugin {
    use super::{DaemonPlugin, Output};
    use crate::agent_error::Result;
    use async_trait::async_trait;
    use emf_wire_types::AgentResult;
    use futures::{future, Future, TryFutureExt};
    use std::{
        pin::Pin,
        sync::{
            atomic::{AtomicUsize, Ordering},
            Arc,
        },
    };

    async fn as_output(x: impl serde::Serialize + Send) -> Result<Output> {
        Ok(Some(serde_json::to_value(x)?))
    }

    #[derive(Debug, Clone)]
    pub struct TestDaemonPlugin(pub Arc<AtomicUsize>);

    impl Default for TestDaemonPlugin {
        fn default() -> Self {
            Self(Arc::new(AtomicUsize::new(0)))
        }
    }

    #[async_trait]
    impl DaemonPlugin for TestDaemonPlugin {
        fn start_session(&mut self) -> Pin<Box<dyn Future<Output = Result<Output>> + Send>> {
            Box::pin(future::ok(self.0.fetch_add(1, Ordering::Relaxed)).and_then(as_output))
        }
        fn update_session(&self) -> Pin<Box<dyn Future<Output = Result<Output>> + Send>> {
            Box::pin(future::ok(self.0.fetch_add(1, Ordering::Relaxed)).and_then(as_output))
        }
        async fn on_message(&self, body: serde_json::Value) -> Result<AgentResult> {
            Ok(Ok(body))
        }
        async fn teardown(&mut self) -> Result<()> {
            self.0.store(0, Ordering::Relaxed);

            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        get_plugin, mk_callback, test_plugin::TestDaemonPlugin, DaemonPlugin, DaemonPlugins,
    };
    use crate::agent_error::Result;
    use serde_json::json;
    use std::sync::atomic::Ordering;

    #[tokio::test]
    async fn test_daemon_plugin_start_session() -> Result<()> {
        let mut x = TestDaemonPlugin::default();

        let actual = x.start_session().await?;

        assert_eq!(actual, Some(json!(0)));

        assert_eq!(x.0.load(Ordering::SeqCst), 1);

        Ok(())
    }

    #[tokio::test]
    async fn test_daemon_plugin_update_session() -> Result<()> {
        let mut x = TestDaemonPlugin::default();

        x.start_session().await?;
        let actual = x.update_session().await?;

        assert_eq!(actual, Some(json!(1)));

        assert_eq!(x.0.load(Ordering::SeqCst), 2);

        Ok(())
    }

    #[tokio::test]
    async fn test_daemon_plugin_teardown_session() -> Result<()> {
        let mut x = TestDaemonPlugin::default();

        x.start_session().await?;
        x.teardown().await?;

        assert_eq!(x.0.load(Ordering::SeqCst), 0);

        Ok(())
    }

    #[tokio::test]
    async fn test_daemon_plugin_get_from_registry() -> Result<()> {
        let registry: DaemonPlugins = vec![(
            "test_daemon_plugin".into(),
            mk_callback(TestDaemonPlugin::default),
        )]
        .into_iter()
        .collect();

        let mut p1 = get_plugin(&"test_daemon_plugin".into(), &registry)?;

        let actual = p1.start_session().await?;

        assert_eq!(actual, Some(json!(0)));

        let actual = p1.update_session().await?;

        assert_eq!(actual, Some(json!(1)));

        let mut p2 = get_plugin(&"test_daemon_plugin".into(), &registry)?;

        let actual = p2.start_session().await?;

        assert_eq!(actual, Some(json!(0)));

        Ok(())
    }
}
