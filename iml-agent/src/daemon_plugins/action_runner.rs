// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::{convert, create_registry, Actions, AgentResult},
    agent_error::{ImlAgentError, RequiredError, Result},
    daemon_plugins::DaemonPlugin,
};
use futures::{
    future::{self, Either},
    sync::oneshot,
    Future,
};
use iml_wire_types::{Action, ActionId};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

pub struct ActionRunner {
    ids: Arc<Mutex<HashMap<ActionId, oneshot::Sender<()>>>>,
    registry: Actions,
}

impl std::fmt::Debug for ActionRunner {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "ActionRunner {{ ids: {:?}, registry: RegistryFn }}",
            self.ids
        )
    }
}

pub fn create() -> impl DaemonPlugin {
    ActionRunner {
        ids: Arc::new(Mutex::new(HashMap::new())),
        registry: create_registry(),
    }
}

impl DaemonPlugin for ActionRunner {
    fn on_message(
        &mut self,
        v: serde_json::Value,
    ) -> Box<Future<Item = AgentResult, Error = ImlAgentError> + Send> {
        let action: Action = match serde_json::from_value(v) {
            Ok(x) => x,
            Err(e) => return Box::new(future::err(ImlAgentError::Serde(e))),
        };

        match action {
            Action::ActionStart { action, args, id } => {
                let action_plugin_fn = match self.registry.get_mut(&action) {
                    Some(p) => p,
                    None => {
                        return Box::new(future::ok(convert::<()>(Err(RequiredError(
                            "action and args required to start action".to_string(),
                        )
                        .into()))));
                    }
                };

                let (tx, rx) = oneshot::channel();

                match self.ids.lock() {
                    Ok(mut x) => x.insert(id.clone(), tx),
                    Err(e) => return Box::new(future::err(e.into())),
                };

                let fut = action_plugin_fn(args);

                let ids = self.ids.clone();

                Box::new(
                    fut.select2(rx)
                        .map(move |r| match r {
                            Either::A((b, _)) => {
                                ids.lock().unwrap().remove(&id);
                                b
                            }
                            Either::B((_, z)) => {
                                drop(z);
                                convert(Ok(()))
                            }
                        })
                        .map_err(|e| match e {
                            _ => unreachable!(),
                        }),
                )
            }
            Action::ActionCancel { id } => {
                let tx = match self.ids.lock() {
                    Ok(mut x) => x.remove(&id),
                    Err(e) => return Box::new(future::err(e.into())),
                };

                if let Some(tx) = tx {
                    // We don't care what the result is here.
                    tx.send(()).is_ok();
                }

                Box::new(future::ok(convert(Ok(()))))
            }
        }
    }
    fn teardown(&mut self) -> Result<()> {
        for (_, tx) in self.ids.lock()?.drain() {
            // We don't care what the result is here.
            tx.send(()).is_ok();
        }

        Ok(())
    }
}
