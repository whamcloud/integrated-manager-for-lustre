// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::EmfAgentError,
    daemon_plugins::{DaemonPlugin, Output},
    env,
    http_comms::streaming_client::send,
};
use async_trait::async_trait;
use futures::{
    stream::{StreamExt as _, TryStreamExt},
    Future, FutureExt,
};
use inotify::{Inotify, WatchMask};
use std::{
    collections::{HashMap, HashSet},
    pin::Pin,
    sync::Arc,
};
use stream_cancel::{Trigger, Tripwire};
use tokio::{fs, net::UnixListener, sync::Mutex};
use tokio_util::codec::{BytesCodec, FramedRead};

#[derive(Clone)]
pub struct PostOffice {
    // individual mailbox socket listeners
    routes: Arc<Mutex<HashMap<String, Trigger>>>,
    trigger: Option<Arc<Trigger>>,
}

pub fn create() -> impl DaemonPlugin {
    PostOffice {
        routes: Arc::new(Mutex::new(HashMap::new())),
        trigger: None,
    }
}

impl std::fmt::Debug for PostOffice {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "PostOffice {{ {:?} }}", self.routes)
    }
}

// Returned trigger should be dropped to cause route to stop
fn start_route(mailbox: String) -> Trigger {
    let (trigger, tripwire) = Tripwire::new();
    let addr = env::mailbox_sock(&mailbox);

    let rc = async move {
        // remove old unix socket
        let _ = fs::remove_file(&addr).await.map_err(|e| {
            tracing::debug!("Failed to remove file {}: {}", &addr, &e);
        });
        let mut listener = UnixListener::bind(addr.clone()).map_err(|e| {
            tracing::error!("Failed to open unix socket {}: {}", &addr, &e);
            e
        })?;
        let mut incoming = listener.incoming().take_until(tripwire);

        tracing::debug!("Starting Route for {}", mailbox);
        while let Some(inbound) = incoming.next().await {
            match inbound {
                Ok(inbound) => {
                    let stream = FramedRead::new(inbound, BytesCodec::new())
                        .map_ok(bytes::BytesMut::freeze)
                        .err_into();
                    let transfer = send("mailbox", mailbox.clone(), stream).map(|r| {
                        if let Err(e) = r {
                            tracing::error!("Failed to transfer: {}", e);
                        }
                    });
                    tokio::spawn(transfer);
                }
                Err(e) => tracing::error!("Failed transfer: {}", e),
            }
        }
        tracing::debug!("Ending Route for {}", mailbox);
        fs::remove_file(&addr).await.map_err(|e| {
            tracing::error!("Failed to remove socket {}: {}", &addr, &e);
            e
        })
    };
    tokio::spawn(rc);
    trigger
}

#[async_trait]
impl DaemonPlugin for PostOffice {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, EmfAgentError>> + Send>> {
        let routes = Arc::clone(&self.routes);
        let mut inotify = Inotify::init().expect("Failed to initialize inotify");
        let conf_file = env::get_var("POSTMAN_CONF_PATH");

        let (trigger, tripwire) = Tripwire::new();

        self.trigger = Some(Arc::new(trigger));

        async move {
            if let Ok(file) = fs::read_to_string(&conf_file).await {
                let itr = file.lines().map(|mb| {
                    let trigger = start_route(mb.to_string());
                    (mb.to_string(), trigger)
                });
                routes.lock().await.extend(itr);
            } else {
                fs::OpenOptions::new()
                    .write(true)
                    .create(true)
                    .open(&conf_file)
                    .await?;
            }

            inotify
                .add_watch(&conf_file, WatchMask::MODIFY)
                .map_err(|e| tracing::error!("Failed to watch configuration: {}", e))
                .ok();

            let watcher = async move {
                let mut buffer = [0; 32];
                let stream = inotify.event_stream(&mut buffer)?;
                let mut events = stream.take_until(tripwire);

                while let Some(ev) = events.next().await {
                    tracing::debug!("inotify event: {:?}", ev);
                    match fs::read_to_string(&conf_file).await {
                        Ok(file) => {
                            let newset: HashSet<String> =
                                file.lines().map(|s| s.to_string()).collect();
                            let oldset: HashSet<String> =
                                routes.lock().await.keys().cloned().collect();

                            let added = &newset - &oldset;
                            let itr = added.iter().map(|mb| {
                                let trigger = start_route(mb.to_string());
                                (mb.to_string(), trigger)
                            });
                            let mut rt = routes.lock().await;
                            rt.extend(itr);
                            for rm in &oldset - &newset {
                                rt.remove(&rm);
                            }
                        }
                        Err(e) => {
                            tracing::error!("Failed to open configuration {}: {}", &conf_file, e)
                        }
                    };
                }
                tracing::debug!("Ending Inotify Listen for {}", &conf_file);
                Ok::<_, EmfAgentError>(())
            };

            tokio::spawn(watcher);
            Ok(None)
        }
        .boxed()
    }

    async fn teardown(&mut self) -> Result<(), EmfAgentError> {
        // drop all triggers
        self.routes.lock().await.clear();
        self.trigger.take();
        Ok(())
    }
}
