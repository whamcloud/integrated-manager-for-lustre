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
    lustre::lctl,
};
use async_trait::async_trait;
use futures::{
    future::{join_all, AbortHandle, Abortable},
    lock::Mutex,
    Future, FutureExt,
};
use iml_cmd::CmdError;
use iml_tracing::tracing;
use iml_wire_types::snapshot::{List, Snapshot};
use std::collections::BTreeSet;
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

async fn list() -> Result<Vec<Snapshot>, ()> {
    let fss: Vec<String> = lctl(vec!["get_param", "-N", "mgs.MGS.live.*"])
        .await
        .map_err(|e| {
            // XXX debug because of false positives. But this is still a failure.
            tracing::debug!("listing filesystems failed: {}", e);
        })
        .map(|o| {
            o.lines()
                .map(|line| line.split('.').nth(3).unwrap().to_string())
                .filter(|n| n != "params")
                .collect()
        })?;

    tracing::debug!("filesystems: {:?}", &fss);

    let futs = fss.into_iter().map(|fs| async move {
        snapshot::list(List {
            fsname: fs.clone(),
            name: None,
        })
        .await
        .map_err(|e| (fs, e))
    });

    let (oks, errs): (Vec<_>, Vec<_>) = join_all(futs).await.into_iter().partition(Result::is_ok);

    let snaps = oks
        .into_iter()
        .map(|x| x.unwrap())
        .flatten()
        .collect::<Vec<Snapshot>>();

    let snapshot_fsnames = snaps
        .iter()
        .map(|s| &s.snapshot_fsname)
        .collect::<BTreeSet<&String>>();

    let really_failed_fss = errs
        .into_iter()
        .map(|x| x.unwrap_err())
        .filter(|x| {
            tracing::debug!("listing for {} failed: {:?}", x.0, x.1);

            if snapshot_fsnames.contains(&x.0) {
                tracing::debug!("{} is a snapshot FS", x.0);
                return false;
            }

            match &x.1 {
                ImlAgentError::CmdError(CmdError::Output(o)) => {
                    // XXX lctl returns 1 no matter what, so have to read its output:
                    let stderr = String::from_utf8_lossy(&o.stderr);
                    stderr.find("Miss MDT0 in the config file").is_none()
                }
                _ => true,
            }
        })
        .collect::<Vec<_>>();

    if really_failed_fss.is_empty() {
        Ok(snaps)
    } else {
        tracing::error!("listing failed: {:?}", really_failed_fss);
        Err(())
    }
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
                        if let Ok(snapshots) = list().await {
                            tracing::debug!("snapshots ({}): {:?}", snapshots.len(), &snapshots);

                            let output = serde_json::to_value(snapshots).map(Some).unwrap();
                            let mut lock = state.lock().await;
                            if lock.output != output {
                                lock.output = output;
                                lock.updated = true;
                            }
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
