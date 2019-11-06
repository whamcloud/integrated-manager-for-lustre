// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::{create_registry, Actions},
    agent_error::{ImlAgentError, RequiredError, Result},
    daemon_plugins::DaemonPlugin,
};
use futures::{
    channel::oneshot,
    future::{self, Either},
    Future, FutureExt,
};
use iml_wire_types::{Action, ActionId, ActionResult, AgentResult, ToJsonValue};
use parking_lot::Mutex;
use std::{collections::HashMap, pin::Pin, sync::Arc};

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
        &self,
        v: serde_json::Value,
    ) -> Pin<Box<dyn Future<Output = Result<AgentResult>> + Send>> {
        let action: Action = match serde_json::from_value(v) {
            Ok(x) => x,
            Err(e) => return Box::pin(future::err(ImlAgentError::Serde(e))),
        };

        match action {
            Action::ActionStart { action, args, id } => {
                let action_plugin_fn = match self.registry.get(&action) {
                    Some(p) => p,
                    None => {
                        let err =
                            RequiredError(format!("Could not find action {} in registry", action));

                        let result = ActionResult {
                            id,
                            result: Err(format!("{:?}", err)),
                        };

                        return Box::pin(future::ok(result.to_json_value()));
                    }
                };

                let (tx, rx) = oneshot::channel();

                self.ids.lock().insert(id.clone(), tx);

                let fut = action_plugin_fn(args);

                let ids = self.ids.clone();

                Box::pin(
                    future::select(fut, rx)
                        .map(move |r| match r {
                            Either::Left((result, _)) => {
                                ids.lock().remove(&id);
                                ActionResult { id, result }
                            }
                            Either::Right((_, z)) => {
                                drop(z);
                                ActionResult {
                                    id,
                                    result: ().to_json_value(),
                                }
                            }
                        })
                        .map(|r| Ok(r.to_json_value())),
                )
            }
            Action::ActionCancel { id } => {
                let tx = self.ids.lock().remove(&id);

                if let Some(tx) = tx {
                    // We don't care what the result is here.
                    let _ = tx.send(()).is_ok();
                }

                Box::pin(future::ok(
                    ActionResult {
                        id,
                        result: ().to_json_value(),
                    }
                    .to_json_value(),
                ))
            }
        }
    }
    fn teardown(&mut self) -> Result<()> {
        for (_, tx) in self.ids.lock().drain() {
            // We don't care what the result is here.
            let _ = tx.send(()).is_ok();
        }

        Ok(())
    }
}
