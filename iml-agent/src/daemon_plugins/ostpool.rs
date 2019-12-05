// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::ostpool::{ost_list, pool_list, pools},
    agent_error::ImlAgentError,
    cmd::lctl,
    daemon_plugins::{DaemonPlugin, Output},
};
use futures::{future::try_join_all, lock::Mutex, Future, FutureExt};
use iml_wire_types::{OstPool, OstPoolAction};
use std::{
    collections::{HashMap, HashSet},
    pin::Pin,
    sync::Arc,
};

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

            let xs = fslist.into_iter().map(|fsname| {
                let fsmap: HashMap<String, Vec<String>> = HashMap::new();
                let state = Arc::clone(&state);
                async move {
                    state.lock().await.insert(fsname.clone(), fsmap);

                    let xs = pool_list(&fsname)
                        .await
                        .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                        .unwrap()
                        .into_iter()
                        .map(|pool| {
                            let fsname = fsname.clone();
                            let state = Arc::clone(&state);
                            async move {
                                if let Ok(osts) = ost_list(&fsname, &pool)
                                    .await
                                    .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                                {
                                    state
                                        .lock()
                                        .await
                                        .get_mut(&fsname)
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
        let state = Arc::clone(&self.state);

        async move {
            let fslist = list_fs()
                .await
                .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                .unwrap();

            let xs = fslist.into_iter().map(|fs| {
                let state = Arc::clone(&state);

                async move {
                    if let Some(hm) = state.lock().await.get_mut(&fs) {
                        let pools = pools(fs.clone()).await?;

                        let mut rmlist = hm.clone();
                        let mut changes: Vec<(OstPoolAction, OstPool)> = vec![];
                        for pool in pools.iter() {
                            tracing::debug!("Updating {}.{}", fs, pool.name);

                            if let Some(oldosts) = rmlist.remove(&pool.name) {
                                let new: HashSet<_> = pool.osts.iter().cloned().collect();
                                let old: HashSet<_> = oldosts.iter().cloned().collect();

                                let addlist: HashSet<_> = new.difference(&old).cloned().collect();
                                if !addlist.is_empty() {
                                    hm.insert(
                                        pool.name.clone(),
                                        old.union(&addlist).cloned().collect(),
                                    );
                                    changes.push((
                                        OstPoolAction::Grow,
                                        OstPool {
                                            name: pool.name.clone(),
                                            filesystem: fs.clone(),
                                            osts: addlist.iter().cloned().collect(),
                                        },
                                    ));
                                }

                                let remlist: Vec<String> = old.difference(&new).cloned().collect();
                                if !remlist.is_empty() {
                                    changes.push((
                                        OstPoolAction::Shrink,
                                        OstPool {
                                            name: pool.name.clone(),
                                            filesystem: fs.clone(),
                                            osts: remlist,
                                        },
                                    ));
                                }
                                hm.insert(pool.name.clone(), pool.osts.clone());
                            } else {
                                hm.insert(pool.name.clone(), pool.osts.clone());
                                changes.push((OstPoolAction::Add, pool.clone()));
                            }
                        }

                        // Removed pools
                        for name in rmlist.keys() {
                            let osts = match hm.remove(&name.clone()) {
                                Some(o) => o.clone(),
                                None => vec![],
                            };
                            changes.push((
                                OstPoolAction::Remove,
                                OstPool {
                                    name: name.clone(),
                                    filesystem: fs.clone(),
                                    osts,
                                },
                            ));
                        }
                        Ok(changes)
                    } else {
                        // Need to create filesystem in self.state
                        let fsmap: HashMap<String, Vec<String>> = HashMap::new();
                        state.lock().await.insert(fs.clone(), fsmap);

                        let xs = pool_list(&fs)
                            .await
                            .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                            .unwrap()
                            .into_iter()
                            .map(|pool| {
                                let fsname = fs.clone();
                                let state = Arc::clone(&state);
                                async move {
                                    if let Ok(osts) = ost_list(&fsname, &pool)
                                        .await
                                        .map_err(|_| Ok::<Vec<String>, ImlAgentError>(vec![]))
                                    {
                                        state
                                            .lock()
                                            .await
                                            .get_mut(&fsname)
                                            .and_then(|hm| hm.insert(pool, osts));
                                    }
                                    Ok::<(), ImlAgentError>(())
                                }
                            });
                        try_join_all(xs).await?;

                        let l = state.lock().await.get(&fs).map_or(vec![], |phm| {
                            phm.iter()
                                .map(move |(pool, osts)| {
                                    (
                                        OstPoolAction::Initial,
                                        OstPool {
                                            name: pool.clone(),
                                            filesystem: fs.clone(),
                                            osts: osts.clone(),
                                        },
                                    )
                                })
                                .collect()
                        });
                        Ok::<Vec<(OstPoolAction, OstPool)>, ImlAgentError>(l)
                    }
                }
            });
            let list: Vec<(OstPoolAction, OstPool)> =
                try_join_all(xs).await?.iter().cloned().flatten().collect();
            if list.is_empty() {
                Ok(None)
            } else {
                let x = serde_json::to_value(list).map(Some)?;
                Ok(x)
            }
        }
            .boxed()
    }
}
