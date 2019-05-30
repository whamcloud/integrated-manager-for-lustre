// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{action_plugins::stratagem::server, agent_error::ImlAgentError};
use futures::{future::IntoFuture, Future};
use iml_wire_types::{ActionName, ToJsonValue};
use std::collections::HashMap;

type BoxedFuture = Box<
    Future<Item = std::result::Result<serde_json::value::Value, String>, Error = ()>
        + 'static
        + Send,
>;

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
            .from_err()
            .and_then(f)
            .then(|x| {
                Ok(match x {
                    Ok(x) => x.to_json_value(),
                    Err(e) => Err(format!("{}", e)),
                })
            }),
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

/// The registry of available actions to the `AgentDaemon`.
/// Add new Actions to the fn body as they are created.
pub fn create_registry() -> HashMap<ActionName, Callback> {
    let mut map = HashMap::new();

    map.insert(
        "start_scan_stratagem".into(),
        mk_callback(&server::trigger_scan),
    );

    map.insert(
        "stream_fidlists_stratagem".into(),
        mk_callback(&server::stream_fidlists),
    );

    log::info!("Loaded the following ActionPlugins:");

    for ActionName(key) in map.keys() {
        log::info!("{}", key)
    }

    map
}
