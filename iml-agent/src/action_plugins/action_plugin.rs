// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::stratagem::{action_purge, action_warning, server},
    action_plugins::{check_ha, check_stonith, check_stratagem, ostpool},
    agent_error::ImlAgentError,
    systemd,
};
use futures::{Future, FutureExt};
use iml_wire_types::{ActionName, ToJsonValue};
use std::{collections::HashMap, pin::Pin};
use tracing::info;

type BoxedFuture = Pin<Box<dyn Future<Output = Result<serde_json::value::Value, String>> + Send>>;

type Callback = Box<dyn Fn(serde_json::value::Value) -> BoxedFuture + Send + Sync>;

async fn run_plugin<T, R, Fut>(
    v: serde_json::value::Value,
    f: fn(T) -> Fut,
) -> Result<serde_json::value::Value, String>
where
    T: serde::de::DeserializeOwned + Send,
    R: serde::Serialize + Send,
    Fut: Future<Output = Result<R, ImlAgentError>> + Send,
{
    let x = serde_json::from_value(v).map_err(|e| format!("{}", e))?;

    let x = f(x).await.map_err(|e| format!("{}", e))?;

    x.to_json_value()
}

fn mk_callback<Fut, T, R>(f: fn(T) -> Fut) -> Callback
where
    Fut: Future<Output = Result<R, ImlAgentError>> + Send + 'static,
    T: serde::de::DeserializeOwned + Send + 'static,
    R: serde::Serialize + Send + 'static,
{
    Box::new(move |v| run_plugin(v, f).boxed())
}

pub type Actions = HashMap<ActionName, Callback>;

/// The registry of available actions to the `AgentDaemon`.
/// Add new Actions to the fn body as they are created.
pub fn create_registry() -> HashMap<ActionName, Callback> {
    let mut map = HashMap::new();

    map.insert("start_unit".into(), mk_callback(systemd::start_unit));

    map.insert("stop_unit".into(), mk_callback(systemd::stop_unit));

    map.insert("enable_unit".into(), mk_callback(systemd::enable_unit));

    map.insert("disable_unit".into(), mk_callback(systemd::disable_unit));

    map.insert(
        "get_unit_run_state".into(),
        mk_callback(systemd::get_run_state),
    );

    map.insert(
        "start_scan_stratagem".into(),
        mk_callback(server::trigger_scan),
    );

    map.insert(
        "stream_fidlists_stratagem".into(),
        mk_callback(server::stream_fidlists),
    );

    map.insert(
        "action_warning_stratagem".into(),
        mk_callback(action_warning::read_mailbox),
    );

    map.insert(
        "action_purge_stratagem".into(),
        mk_callback(action_purge::read_mailbox),
    );

    map.insert("action_check_ha".into(), mk_callback(check_ha::check_ha));

    map.insert(
        "action_check_stonith".into(),
        mk_callback(check_stonith::check_stonith),
    );

    map.insert(
        "action_check_stratagem".into(),
        mk_callback(check_stratagem::check_stratagem),
    );

    map.insert(
        "ostpool_create".into(),
        mk_callback(ostpool::action_pool_create),
    );

    map.insert(
        "ostpool_wait".into(),
        mk_callback(ostpool::action_pool_wait),
    );

    map.insert(
        "ostpool_destroy".into(),
        mk_callback(ostpool::action_pool_destroy),
    );

    map.insert("ostpool_add".into(), mk_callback(ostpool::action_pool_add));

    map.insert(
        "ostpool_remove".into(),
        mk_callback(ostpool::action_pool_remove),
    );

    info!("Loaded the following ActionPlugins:");

    for ActionName(key) in map.keys() {
        info!("{}", key)
    }

    map
}
