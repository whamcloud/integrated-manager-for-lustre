// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::ostpool::{ost_list, pool_list},
    agent_error::ImlAgentError,
    cmd::lctl,
    daemon_plugins::{DaemonPlugin, Output},
};
use futures::{
    future::{self, try_join_all},
    lock::Mutex,
    Future, FutureExt,
};
use iml_wire_types::{OstPool, OstPoolAction};
use std::{collections::HashMap, pin::Pin, sync::Arc};

#[derive(Debug)]
pub struct PoolState {
    state: Arc<Mutex<HashMap<String, HashMap<String, Vec<String>>>>>,
}

pub fn create() -> impl DaemonPlugin {
    PoolState {
        state: Arc::new(Mutex::new(HashMap::new())),
    }
}

async fn list_fs() -> Result<Vec<String>, ImlAgentError> {
    match lctl(vec!["get_param", "-N", "mdt.*-MDT0000"]).await {
        Err(_) => Ok(vec![]),
        Ok(o) => Ok(String::from_utf8_lossy(&o.stdout)
            .lines()
            .filter_map(|line| {
                let mut parts = line.split('.').skip(1);
                if let Some(mdt) = parts.next() {
                    mdt.split("-MDT").next()
                } else {
                    None
                }
            })
            .map(|s| s.to_string())
            .collect()),
    }
}

impl DaemonPlugin for PoolState {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let fslist = list_fs()
                .await
                .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                .unwrap();

            let xs = fslist.into_iter().map(|fs| {
                let fsmap: HashMap<String, Vec<String>> = HashMap::new();
                let state = Arc::clone(&state);

                async move {
                    state.lock().await.insert(fs.clone(), fsmap);
                    let xs = pool_list(&fs)
                        .await
                        .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                        .unwrap()
                        .into_iter()
                        .map(|pool| {
                            let fs = fs.clone();
                            let state = Arc::clone(&state);
                            async move {
                                if let Ok(osts) = ost_list(&fs, &pool)
                                    .await
                                    .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                                {
                                    state
                                        .lock()
                                        .await
                                        .get_mut(&fs)
                                        .and_then(|hm| hm.insert(pool, osts));
                                }
                                Ok::<(), ImlAgentError>(())
                            }
                        });
                    try_join_all(xs).await
                }
            });
            try_join_all(xs).await?;
            let pools: Vec<(OstPoolAction, OstPool)> = state
                .lock()
                .await
                .iter()
                .map(|(fs, phm)| {
                    let fs = fs.clone();
                    phm.iter().map(move |(pool, osts)| {
                        (
                            OstPoolAction::Initial,
                            OstPool {
                                name: pool.clone(),
                                filesystem: fs.clone(),
                                osts: osts.clone(),
                                ..Default::default()
                            },
                        )
                    })
                })
                .flatten()
                .collect();
            let x = serde_json::to_value(pools).map(Some)?;
            Ok(x)
        }
            .boxed()
    }

    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        // @@ diff
        future::ok(None).boxed()
    }
}
