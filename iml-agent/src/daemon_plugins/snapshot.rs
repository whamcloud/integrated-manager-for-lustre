// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Snapshot listing plugin
//!
//! This module is responsible for continually discovering snapshots of filesystems.
//!
//!

use crate::{
    action_plugins::lustre::snapshot,
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
    lustre::list_fs,
};
use async_trait::async_trait;
use futures::{
    future::{join_all, AbortHandle, Abortable},
    lock::Mutex,
    Future, FutureExt,
};
use iml_wire_types::snapshot::{List, Snapshot};
use std::{pin::Pin, sync::Arc, time::Duration};
use tokio::time::delay_for;

struct State {
    updated: bool,
    output: Output,
}

#[derive(Debug)]
pub(crate) struct SnapshotList {
    reader: Option<AbortHandle>,
    state: Arc<Mutex<State>>,
}

pub(crate) fn create() -> SnapshotList {
    SnapshotList {
        reader: None,
        state: Arc::new(Mutex::new(State {
            updated: false,
            output: None,
        })),
    }
}

async fn list() -> Result<Vec<Snapshot>, ImlAgentError> {
    let fss = list_fs().await?;
    tracing::debug!("filesystems: {:?}", &fss);

    let futs = fss.into_iter().map(|fs| {
        snapshot::list(List {
            fsname: fs,
            name: None,
            detail: false,
        })
    });

    join_all(futs)
        .await
        .into_iter()
        .collect::<Result<Vec<_>, _>>()
        .map(|ss| ss.into_iter().flatten().collect())
}

#[async_trait]
impl DaemonPlugin for SnapshotList {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        let (reader, reader_reg) = AbortHandle::new_pair();
        self.reader = Some(reader);

        async move {
            tokio::spawn(Abortable::new(
                async move {
                    loop {
                        match list().await {
                            Err(e) => {
                                tracing::warn!("listing snapshots failed: {}", e);
                            }
                            Ok(snapshots) => {
                                tracing::debug!(
                                    "snapshots - {}: {:?}",
                                    snapshots.len(),
                                    &snapshots
                                );

                                let output = serde_json::to_value(snapshots).map(Some).unwrap();
                                let mut lock = state.lock().await;
                                if lock.output != output {
                                    lock.output = output;
                                    lock.updated = true;
                                }
                            }
                        };
                        delay_for(Duration::from_secs(60)).await;
                    }
                },
                reader_reg,
            ));
            Ok(None)
        }
        .boxed()
    }

    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);
        async move {
            let mut lock = state.lock().await;

            if lock.updated {
                lock.updated = false;
                Ok(lock.output.clone())
            } else {
                Ok(None)
            }
        }
        .boxed()
    }

    async fn teardown(&mut self) -> Result<(), ImlAgentError> {
        if let Some(reader) = &self.reader {
            reader.abort();
            self.reader = None;
        }

        Ok(())
    }
}
