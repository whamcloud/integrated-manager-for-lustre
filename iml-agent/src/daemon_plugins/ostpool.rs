// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::ostpool::{ost_list, pool_list, pools},
    agent_error::ImlAgentError,
    cmd::lctl,
    daemon_plugins::{DaemonPlugin, Output},
};
use futures::{future::{join_all, try_join_all}, lock::Mutex, Future, FutureExt};
use iml_wire_types::{OstPool, OstPoolAction};
use std::{
    collections::{HashMap, HashSet},
    iter::FromIterator,
    pin::Pin,
    sync::Arc,
};

#[derive(Debug)]
pub struct PoolState {
    state: Arc<Mutex<HashMap<String, HashMap<String, HashSet<String>>>>>,
}

pub fn create() -> impl DaemonPlugin {
    PoolState {
        state: Arc::new(Mutex::new(HashMap::new())),
    }
}

async fn list_fs() -> Result<Vec<String>, ImlAgentError> {
    Ok(lctl(vec!["get_param", "-N", "mdt.*-MDT0000"])
        .await
        .map(|o| {
            String::from_utf8_lossy(&o.stdout)
                .lines()
                .filter_map(|line| {
                    line.split('.')
                        .skip(1)
                        .next()
                        .and_then(|mdt| mdt.split("-MDT").next())
                })
                .map(|s| s.to_string())
                .collect()
        })
        .unwrap_or(vec![]))
}

/// Return vector of changes between existing fs state and list of pools
/// from current filesystem
fn diff_state(
    fs: String,
    state: &mut HashMap<String, HashSet<String>>,
    pools: &Vec<OstPool>,
) -> Result<Vec<(OstPoolAction, OstPool)>, ImlAgentError> {
    let mut rmlist = state.clone();
    let mut changes: Vec<(OstPoolAction, OstPool)> = vec![];
    for pool in pools {
        tracing::debug!("Updating {}.{}", fs, pool.name);

        if let Some(old) = rmlist.remove(&pool.name) {
            let new = HashSet::from_iter(pool.osts.clone());

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
            state.insert(pool.name.clone(), pool.osts.iter().cloned().collect());
        } else {
            state.insert(pool.name.clone(), pool.osts.iter().cloned().collect());
            changes.push((OstPoolAction::Add, pool.clone()));
        }
    }

    // Removed pools
    for name in rmlist.keys() {
        let osts = state.remove(name.as_str()).unwrap_or(HashSet::new());
        changes.push((
            OstPoolAction::Remove,
            OstPool {
                name: name.clone(),
                filesystem: fs.clone(),
                osts: osts.into_iter().collect(),
            },
        ));
    }
    Ok(changes)
}

async fn get_fsmap(
    fsname: String,
) -> Vec<(String, String, HashSet<String>)> {
    let xs = pool_list(&fsname)
        .await
        .unwrap_or(vec![])
        .into_iter()
        .map(|pool| {
            let fsname = fsname.clone();
            async move {
                let osts = ost_list(&fsname, &pool).await.unwrap_or(HashSet::new());
                (fsname, pool, osts)
            }
        });
    join_all(xs).await
}

fn init_pools(
    state: &mut HashMap<String, HashMap<String, HashSet<String>>>,
    xs: Vec<(String, String, HashSet<String>)>,
) -> Vec<(OstPoolAction, OstPool)> {
    xs.into_iter()
        .inspect(|(fsname, pool, osts)| {
            state
                .entry(fsname.clone())
                .and_modify(|hm| {
                    hm.insert(pool.clone(), osts.clone());
                })
                .or_insert_with(|| HashMap::from_iter(vec![(pool.clone(), osts.clone())]));
        })
        .map(|(filesystem, name, osts)| {
            (
                OstPoolAction::Initial,
                OstPool {
                    name,
                    filesystem,
                    osts: osts.into_iter().collect(),
                },
            )
        })
        .collect()
}

impl DaemonPlugin for PoolState {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let fslist = list_fs().await.unwrap_or(vec![]);

            let xs = join_all(fslist.into_iter().map(get_fsmap))
                .await
                .into_iter()
                .flatten()
                .collect();

            let mut state = state.lock().await;
            
            let pools: Vec<(OstPoolAction, OstPool)> = init_pools(&mut state, xs);

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
                        let xs = get_fsmap(fs).await;
                        
                        let mut state = state.lock().await;

                        let pools: Vec<(OstPoolAction, OstPool)> = init_pools(&mut state, xs);

                        Ok::<Vec<(OstPoolAction, OstPool)>, ImlAgentError>(pools)
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
