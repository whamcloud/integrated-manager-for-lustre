// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::create_registry,
    agent_error::{EmfAgentError, RequiredError, Result},
    daemon_plugins::DaemonPlugin,
};
use async_trait::async_trait;
use emf_util::action_plugins::Actions;
use emf_wire_types::{Action, ActionId, ActionResult, AgentResult, ToJsonValue};
use futures::{
    channel::oneshot,
    future::{self, Either},
};
use std::{collections::HashMap, sync::Arc};
use tokio::sync::Mutex;

#[derive(Clone)]
pub struct ActionRunner {
    ids: Arc<Mutex<HashMap<ActionId, oneshot::Sender<()>>>>,
    registry: Arc<Actions>,
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
        registry: Arc::new(create_registry()),
    }
}

#[async_trait]
impl DaemonPlugin for ActionRunner {
    async fn on_message(&self, v: serde_json::Value) -> Result<AgentResult> {
        let action: Action = match serde_json::from_value(v) {
            Ok(x) => x,
            Err(e) => return Err(EmfAgentError::SerdeJson(e)),
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

                        return Ok(result.to_json_value());
                    }
                };

                let (tx, rx) = oneshot::channel();

                self.ids.lock().await.insert(id.clone(), tx);

                let fut = action_plugin_fn(args);

                let ids = self.ids.clone();

                let r = future::select(fut, rx).await;

                let r = match r {
                    Either::Left((result, _)) => {
                        ids.lock().await.remove(&id);
                        ActionResult { id, result }
                    }
                    Either::Right((_, z)) => {
                        drop(z);
                        ActionResult {
                            id,
                            result: ().to_json_value(),
                        }
                    }
                };

                Ok(r.to_json_value())
            }
            Action::ActionCancel { id } => {
                let tx = self.ids.lock().await.remove(&id);

                if let Some(tx) = tx {
                    // We don't care what the result is here.
                    let _ = tx.send(()).is_ok();
                }

                Ok(ActionResult {
                    id,
                    result: ().to_json_value(),
                }
                .to_json_value())
            }
        }
    }
    async fn teardown(&mut self) -> Result<()> {
        for (_, tx) in self.ids.lock().await.drain() {
            // We don't care what the result is here.
            let _ = tx.send(()).is_ok();
        }

        Ok(())
    }
}
