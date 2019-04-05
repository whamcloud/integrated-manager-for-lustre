// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{ImlAgentError, NoPluginError, Result},
    daemon_plugins::{action_runner, stratagem},
};
use futures::{future, Future};
use iml_wire_types::{AgentResult, PluginName, ToJsonValue};
use std::collections::HashMap;

pub type OutputValue = serde_json::Value;
pub type Output = Option<OutputValue>;

pub fn as_output(x: impl serde::Serialize + Send + 'static) -> Result<Output> {
    Ok(Some(serde_json::to_value(x)?))
}

/// Plugin interface for extensible behavior
/// between the agent and manager.
///
/// Maintains internal state and sends and receives messages.
///
/// Implementors of this trait should add themselves
/// to the `plugin_registry` below.
pub trait DaemonPlugin: std::fmt::Debug {
    /// Returns full listing of information upon session esablishment
    fn start_session(&self) -> Box<Future<Item = Output, Error = ImlAgentError> + Send> {
        Box::new(future::ok(None))
    }
    /// Return information needed to maintain a manager-agent session, i.e. what
    /// has changed since the start of the session or since the last update.
    ///
    /// If you need to refer to any data from the start_session call, you can
    /// store it as a property on this DaemonPlugin instance.
    ///
    /// This will never be called concurrently with respect to start_session, or
    /// before start_session.
    fn update_session(&self) -> Box<Future<Item = Output, Error = ImlAgentError> + Send> {
        self.start_session()
    }
    /// Handle a message sent from the manager (may be called concurrently with respect to
    /// start_session and update_session).
    fn on_message(
        &mut self,
        _body: serde_json::Value,
    ) -> Box<Future<Item = AgentResult, Error = ImlAgentError> + Send> {
        Box::new(future::ok(().to_json_value()))
    }
    fn teardown(&mut self) -> Result<()> {
        Ok(())
    }
}

pub type DaemonBox = Box<DaemonPlugin + Send + Sync>;

type Callback = Box<Fn() -> DaemonBox + Send + Sync>;

fn mk_callback<D: 'static>(f: &'static (impl Fn() -> D + Sync)) -> Callback
where
    D: DaemonPlugin + Send + Sync,
{
    Box::new(move || Box::new(f()) as DaemonBox)
}

pub type DaemonPlugins = HashMap<PluginName, Callback>;

/// Returns a `HashMap` of plugins available for usage.
pub fn plugin_registry() -> DaemonPlugins {
    let mut hm = HashMap::new();

    hm.insert(
        PluginName("stratagem".into()),
        mk_callback(&stratagem::create),
    );

    hm.insert(
        PluginName("action_runner".into()),
        mk_callback(&action_runner::create),
    );

    log::info!("Loaded the following DaemonPlugins:");

    for PluginName(key) in hm.keys() {
        log::info!("{}", key)
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
