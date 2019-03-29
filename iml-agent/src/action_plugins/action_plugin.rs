// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::manage_stratagem,
    agent_error::{ImlAgentError, Result},
};
use futures::{future::IntoFuture, Future};
use iml_wire_types::ActionName;
use std::collections::HashMap;

pub type AgentResult = std::result::Result<serde_json::Value, String>;

/// Convert a `Result` into an `AgentResult`
pub fn convert<T>(r: Result<T>) -> AgentResult
where
    T: serde::Serialize + 'static + Send,
{
    r.and_then(|x| serde_json::to_value(x).map_err(|e| e.into()))
        .map_err(|e| format!("{:?}", e))
}

type BoxedFuture = Box<Future<Item = AgentResult, Error = ()> + 'static + Send>;

type Callback = Box<Fn(serde_json::value::Value) -> BoxedFuture + Send + Sync>;

fn mk_boxed_future<T: 'static, F: 'static, R, Fut: 'static>(
    v: serde_json::value::Value,
    f: F,
) -> BoxedFuture
where
    T: serde::de::DeserializeOwned + Send,
    R: serde::Serialize + 'static + Send,
    F: Fn(T) -> Fut + Send,
    Fut: Future<Item = R, Error = ImlAgentError> + Send,
{
    Box::new(
        serde_json::from_value(v)
            .into_future()
            .map_err(|e| e.into())
            .and_then(f)
            .then(|x| Ok(convert(x)))
            .map_err(|_: ImlAgentError| ()),
    ) as BoxedFuture
}

fn mk_callback<Fut: 'static, F: 'static, T: 'static, R: 'static>(f: &'static F) -> Callback
where
    Fut: Future<Item = R, Error = ImlAgentError> + Send,
    F: Fn(T) -> Fut + Send + Sync,
    T: serde::de::DeserializeOwned + Send,
    R: serde::Serialize + Send,
{
    Box::new(move |v| mk_boxed_future(v, f))
}

pub type Actions = HashMap<ActionName, Callback>;

/// The registry of available actions to the AgentDaemon.
/// Add new Actions to the fn body as they are created.
pub fn create_registry() -> HashMap<ActionName, Callback> {
    let mut map = HashMap::new();

    map.insert(
        ActionName("start_scan_stratagem".into()),
        mk_callback(&manage_stratagem::start_scan_stratagem),
    );

    log::info!("Loaded the following ActionPlugins:");

    for ActionName(key) in map.keys() {
        log::info!("{}", key)
    }

    map
}
