// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::ostpool::pools,
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
    lustre::lctl,
};
use futures::{future::join_all, lock::Mutex, Future, FutureExt};
use iml_wire_types::{FsPoolMap, OstPool};
use std::{collections::BTreeSet, pin::Pin, sync::Arc};

/// Resend full tree every 5 min
const DEFAULT_RESEND: u32 = 300;

struct PoolStateSub {
    count: u32,
    output: Output,
}

#[derive(Debug)]
pub struct PoolState {
    state: Arc<Mutex<PoolStateSub>>,
}

pub fn create() -> impl DaemonPlugin {
    PoolState {
        state: Arc::new(Mutex::new(PoolStateSub {
            count: DEFAULT_RESEND,
            output: None,
        })),
    }
}

/// List all Lustre Filesystems with MDT0 on this host
async fn list_fs() -> Vec<String> {
    lctl(vec!["get_param", "-N", "mdt.*-MDT0000"])
        .await
        .map(|o| {
            String::from_utf8_lossy(&o.stdout)
                .lines()
                .filter_map(|line| {
                    line.split('.')
                        .nth(1)
                        .and_then(|mdt| mdt.split("-MDT").next())
                })
                .map(|s| s.to_string())
                .collect()
        })
        .unwrap_or_else(|_| vec![])
}

async fn get_fsmap(fsname: String) -> (String, BTreeSet<OstPool>) {
    let xs = pools(fsname.clone())
        .await
        .unwrap_or_else(|_| vec![])
        .into_iter()
        .collect();
    (fsname, xs)
}

async fn build_tree() -> FsPoolMap {
    let fslist = list_fs().await;

    join_all(fslist.into_iter().map(get_fsmap))
        .await
        .into_iter()
        .collect()
}

impl DaemonPlugin for PoolState {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let mut state = state.lock().await;

            let tree = build_tree().await;

            state.output = serde_json::to_value(tree).map(Some)?;

            Ok(state.output.clone())
        }
        .boxed()
    }

    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let tree = build_tree().await;
            let newout = serde_json::to_value(tree).map(Some)?;
            let mut state = state.lock().await;
            state.count -= 1;
            if state.count == 0 || state.output != newout {
                state.count = DEFAULT_RESEND;
                state.output = newout;

                Ok(state.output.clone())
            } else {
                Ok(None)
            }
        }
        .boxed()
    }
}
