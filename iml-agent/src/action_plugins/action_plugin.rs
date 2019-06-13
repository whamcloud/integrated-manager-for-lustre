// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::stratagem::{action_purge, action_warning, server},
    agent_error::ImlAgentError,
};
use futures::{future::IntoFuture, Future};
use iml_wire_types::{ActionName, ToJsonValue};
use std::collections::HashMap;

type BoxedFuture = Box<
    Future<Item = std::result::Result<serde_json::value::Value, String>, Error = ()>
        + 'static
        + Send,
>;

type Callback = Box<Fn(serde_json::value::Value) -> BoxedFuture + Send + Sync>;

fn mk_boxed_future<T, R, Fut>(v: serde_json::value::Value, f: fn(T) -> Fut) -> BoxedFuture
where
    T: serde::de::DeserializeOwned + Send + 'static,
    R: serde::Serialize + 'static + Send,
    Fut: Future<Item = R, Error = ImlAgentError> + Send + 'static,
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

fn mk_callback<Fut, T, R>(f: fn(T) -> Fut) -> Callback
where
    Fut: Future<Item = R, Error = ImlAgentError> + Send + 'static,
    T: serde::de::DeserializeOwned + Send + 'static,
    R: serde::Serialize + Send + 'static,
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
        mk_callback(server::trigger_scan),
    );

    map.insert(
        "stream_fidlists_stratagem".into(),
        mk_callback(server::stream_fidlists),
    );

    map.insert(
        "action_warning_stratagem".into(),
        mk_callback(&action_warning::read_mailbox),
    );
    map.insert(
        "action_purge_stratagem".into(),
        mk_callback(&action_purge::read_mailbox),
    );

    log::info!("Loaded the following ActionPlugins:");

    for ActionName(key) in map.keys() {
        log::info!("{}", key)
    }

    map
}
