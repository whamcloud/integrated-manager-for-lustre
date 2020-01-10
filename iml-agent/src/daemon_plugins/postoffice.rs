// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{ImlAgentError, RequiredError},
    daemon_plugins::{DaemonPlugin, Output},
    http_comms::mailbox_client::send,
};
use futures::stream::TryStreamExt;
use futures::{
    channel::oneshot,
    future::{self, Either},
    Future, FutureExt,
};
use futures_util::stream::StreamExt as ForEachStreamExt;
use iml_wire_types::{Action, ActionId, ActionResult, AgentResult, ToJsonValue};
use parking_lot::Mutex;
use std::{
    collections::{BTreeMap, HashMap},
    pin::Pin,
    sync::Arc,
};
use stream_cancel::{StreamExt, Trigger, Tripwire};
use tokio::{fs, io::AsyncWriteExt, net::UnixListener};
use tokio_util::codec::{BytesCodec, FramedRead};

const CONF_FILE: &str = "/etc/iml/postman.conf";
const SOCK_DIR: &str = "/run/iml/";

pub struct PostOffice {
    // ids of actions (register/deregister)
    ids: Arc<Mutex<HashMap<ActionId, oneshot::Sender<()>>>>,
    // individual mailbox socket listeners
    routes: Arc<Mutex<BTreeMap<String, Trigger>>>,
}

/// Return socket address for a given mailbox
pub fn socket_name(mailbox: &str) -> String {
    format!("{}/postman-{}.sock", SOCK_DIR, mailbox)
}

impl std::fmt::Debug for PostOffice {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "PostOffice {{ ids: {:?}, registry: RegistryFn }}",
            self.ids
        )
    }
}

fn start_route(mailbox: String) -> Trigger {
    let (trigger, tripwire) = Tripwire::new();
    let addr = socket_name(&mailbox);

    let rc = async move {
        let mut listener = UnixListener::bind(addr).unwrap();

        let mut incoming = listener.incoming().take_until(tripwire);
        tracing::debug!("Starting Route for {}", mailbox);
        while let Some(inbound) = incoming.next().await {
            if let Ok(inbound) = inbound {
                let stream = FramedRead::new(inbound, BytesCodec::new())
                    .map_ok(bytes::BytesMut::freeze)
                    .map_err(ImlAgentError::Io);
                let transfer = send(mailbox.clone(), stream).map(|r| {
                    if let Err(e) = r {
                        println!("Failed to transfer; error={}", e);
                    }
                });
                tokio::spawn(transfer);
            }
        }
        tracing::debug!("Ending Route for {}", mailbox);
    };
    tokio::spawn(rc);
    trigger
}

fn stop_route(trigger: Trigger) {
    drop(trigger);
}

async fn write_config(routes: Vec<String>) -> Result<serde_json::value::Value, String> {
    let mut file = fs::File::create(CONF_FILE)
        .await
        .map_err(|e| format!("{}", e))?;
    file.write_all(routes.join("\n").as_bytes())
        .await
        .map_err(|e| format!("{}", e))?;
    file.write(b"\n").await.map_err(|e| format!("{}", e))?;
    ().to_json_value()
}

pub fn create() -> impl DaemonPlugin {
    PostOffice {
        ids: Arc::new(Mutex::new(HashMap::new())),
        routes: Arc::new(Mutex::new(BTreeMap::new())),
    }
}

impl DaemonPlugin for PostOffice {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let routes = Arc::clone(&self.routes);
        let fut = async move {
            if let Ok(file) = fs::read_to_string(CONF_FILE).await {
                let itr = file.lines().map(|mb| {
                    let trigger = start_route(mb.to_string());
                    (mb.to_string(), trigger)
                });
                routes.lock().extend(itr);
            }
            Ok(None)
        };
        fut.boxed()
    }
    fn on_message(
        &self,
        v: serde_json::Value,
    ) -> Pin<Box<dyn Future<Output = Result<AgentResult, ImlAgentError>> + Send>> {
        let action: Action = match serde_json::from_value(v) {
            Ok(x) => x,
            Err(e) => return Box::pin(future::err(ImlAgentError::Serde(e))),
        };

        match action {
            Action::ActionStart { action, args, id } => {
                let mailbox: String = match serde_json::from_value(args) {
                    Ok(x) => x,
                    Err(e) => return Box::pin(future::err(ImlAgentError::Serde(e))),
                };
                match action.0.as_str() {
                    "register" => {
                        self.routes
                            .lock()
                            .entry(mailbox.clone())
                            .or_insert_with(|| start_route(mailbox.clone()));
                    }
                    "deregister" => {
                        if let Some(tx) = self.routes.lock().remove(&mailbox) {
                            stop_route(tx);
                        }
                    }
                    _ => {
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

                let list = self.routes.lock().keys().cloned().collect();
                let fut = Box::pin(write_config(list));

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

    fn teardown(&mut self) -> Result<(), ImlAgentError> {
        for (_, tx) in self.ids.lock().drain() {
            // We don't care what the result is here.
            let _ = tx.send(()).is_ok();
        }
        let keys: Vec<String> = self.routes.lock().keys().cloned().collect();
        let mut routes = self.routes.lock();
        for key in keys {
            if let Some(tx) = routes.remove(&key) {
                stop_route(tx);
            }
        }

        Ok(())
    }
}
