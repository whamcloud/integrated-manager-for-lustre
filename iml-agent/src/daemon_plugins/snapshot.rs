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
    device_scanner_client,
    lustre::list_mdt0s,
};
use async_trait::async_trait;
use futures::{
    future::{try_join_all, AbortHandle, Abortable},
    lock::Mutex,
    Future, FutureExt, TryFutureExt,
};
use iml_wire_types::snapshot::{List, Snapshot};
use std::{
    collections::{HashMap, HashSet},
    pin::Pin,
    sync::Arc,
    time::Duration,
};
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

async fn list() -> Result<Option<HashMap<String, Vec<Snapshot>>>, ImlAgentError> {
    // list the mounts
    // remove any mdt0's that are snapshots
    let snapshot_mounts = device_scanner_client::get_snapshot_mounts()
        .await?
        .into_iter()
        .filter_map(|x| {
            let s = x.opts.0.split(',').find(|x| x.starts_with("svname="))?;

            let s = s.split('=').nth(1)?;

            Some(s.to_string())
        })
        .collect::<HashSet<String>>();

    tracing::debug!("snapshot mounts {:?}", snapshot_mounts);

    let xs = list_mdt0s().await.into_iter().collect::<HashSet<String>>();
    let xs = xs
        .difference(&snapshot_mounts)
        .map(|x| x.to_string())
        .collect::<Vec<String>>();

    tracing::debug!("mdt0s: {:?}", &xs);

    if xs.is_empty() {
        tracing::debug!("No mdt0's. Returning `None`.");

        return Ok(None);
    }

    let xs = xs.into_iter().map(|x| async move {
        let fs_name = x.rsplitn(2, '-').nth(1);
        tracing::debug!("fs_name is: {:?}", fs_name);

        if let Some(fs_name) = fs_name {
            snapshot::list(List {
                target: x.to_string(),
                name: None,
            })
            .inspect_err(|x| {
                tracing::debug!("Error calling snapshot list: {:?}", x);
            })
            .await
            .map(|x| (fs_name.to_string(), x))
        } else {
            tracing::debug!("No fs_name. Returning MarkerNotFound error.");

            Err(ImlAgentError::MarkerNotFound)
        }
    });

    let snapshots: HashMap<String, Vec<Snapshot>> = try_join_all(xs).await?.into_iter().collect();

    tracing::debug!("snapshots: {:?}", snapshots);

    Ok(Some(snapshots))
}

async fn try_update_state(state: &Arc<Mutex<State>>) -> Result<(), ImlAgentError> {
    let snapshots = list().await?;

    let output = snapshots.map(|xs| serde_json::to_value(xs)).transpose()?;

    let mut lock = state.lock().await;

    if lock.output != output {
        tracing::debug!("Snapshot output changed. Updating.");

        lock.output = output;
        lock.updated = true;
    }

    Ok(())
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
                        if let Err(e) = try_update_state(&state).await {
                            tracing::debug!(
                                "Error calling list(): {:?}. Not processing snapshots.",
                                e
                            );
                        }

                        delay_for(Duration::from_secs(10)).await;
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
