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

/// Return vector of changes between existing fs state and list of pools
/// from current filesystem
fn diff_state(
    fs: String,
    state: &mut HashMap<String, Vec<String>>,
    pools: &Vec<OstPool>,
) -> Result<Vec<(OstPoolAction, OstPool)>, ImlAgentError> {
    let mut rmlist = state.clone();
    let mut changes: Vec<(OstPoolAction, OstPool)> = vec![];
    for pool in pools.iter() {
        tracing::debug!("Updating {}.{}", fs, pool.name);

        if let Some(oldosts) = rmlist.remove(&pool.name) {
            let new: HashSet<_> = pool.osts.iter().cloned().collect();
            let old: HashSet<_> = oldosts.into_iter().collect();

            let addlist: HashSet<_> = new.difference(&old).cloned().collect();
            if !addlist.is_empty() {
                state.insert(pool.name.clone(), old.union(&addlist).cloned().collect());
                changes.push((
                    OstPoolAction::Grow,
                    OstPool {
                        name: pool.name.clone(),
                        filesystem: fs.clone(),
                        osts: addlist.into_iter().collect(),
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
            state.insert(pool.name.clone(), pool.osts.clone());
        } else {
            state.insert(pool.name.clone(), pool.osts.clone());
            changes.push((OstPoolAction::Add, pool.clone()));
        }
    }

    // Removed pools
    for name in rmlist.keys() {
        let osts = match state.remove(&name.clone()) {
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
}

async fn init_fsmap(
    state: Arc<Mutex<HashMap<String, HashMap<String, Vec<String>>>>>,
    fsname: String,
) -> Result<(), ImlAgentError> {
    let fsmap: HashMap<String, Vec<String>> = HashMap::new();
    state.lock().await.insert(fsname.clone(), fsmap);

    let xs = pool_list(&fsname)
        .await
        .unwrap_or(vec![])
        .into_iter()
        .map(|pool| {
            let fsname = &fsname;
            let state = Arc::clone(&state);
            async move {
                let osts = ost_list(&fsname, &pool).await.unwrap_or(vec![]);
                state
                    .lock()
                    .await
                    .get_mut(fsname)
                    .and_then(|hm| hm.insert(pool, osts));
                Ok::<(), ImlAgentError>(())
            }
        });
    try_join_all(xs).await?;
    Ok(())
}

impl DaemonPlugin for PoolState {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let fslist = list_fs().await.unwrap_or(vec![]);

            let xs = fslist.into_iter().map(|fsname| {
                let state = Arc::clone(&state);
                async move { init_fsmap(state, fsname).await }
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
            let fslist = list_fs().await.unwrap_or(vec![]);

            let xs = fslist.into_iter().map(|fs| {
                let state = Arc::clone(&state);

                async move {
                    if let Some(hm) = state.lock().await.get_mut(&fs) {
                        let pools = pools(fs.clone()).await?;

                        diff_state(fs, hm, &pools)
                    } else {
                        init_fsmap(Arc::clone(&state), fs.clone()).await?;

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
                try_join_all(xs).await?.into_iter().flatten().collect();
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
