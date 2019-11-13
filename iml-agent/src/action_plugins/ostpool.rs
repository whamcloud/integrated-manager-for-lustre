// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::{ImlAgentError, RequiredError}, cmd::lctl};
use futures::future::try_join_all;
use iml_wire_types::OstPool;
use std::time::{Duration, Instant};
use tokio::timer::delay;

/// A list of rules + a name for the group of rules.
#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct CmdPool {
    pub filesystem: String,
    pub name: String,
}

/// A list of rules + a name for the group of rules.
#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct CmdPoolOst {
    pub filesystem: String,
    pub name: String,
    pub ost: String,
}

pub async fn pool_create(filesystem: String, name: String) -> Result<(), ImlAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_new", &pn]).await.map(drop)
}


/// This needs to be a seperate action from pool_create() since pool create runs on MGS
/// and this runs on MDS
pub async fn action_pool_wait(cmd: CmdPool) -> Result<(), ImlAgentError> {
    let time_to_wait = 120;
    // wait up to a 2 minutes
    for _ in 0_u32..(time_to_wait * 2) {
        let pl = pool_list(&cmd.filesystem).await?;

        if pl.contains(&cmd.name) {
            return Ok(());
        }
        delay(Instant::now() + Duration::from_millis(500)).await;
    }

    Err(ImlAgentError::from(RequiredError(format!(
        "Waiting for pool create {}.{} failed after {} sec",
        cmd.filesystem, cmd.name, time_to_wait))))
}

pub async fn action_pool_create(cmd: CmdPool) -> Result<(), ImlAgentError> {
    pool_create(cmd.filesystem, cmd.name).await
}

pub async fn pool_add(filesystem: String, name: String, ost: String) -> Result<(), ImlAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_add", &pn, ost.as_str()]).await.map(drop)
}

pub async fn action_pool_add(cmd: CmdPoolOst) -> Result<(), ImlAgentError> {
    pool_add(cmd.filesystem, cmd.name, cmd.ost).await
}

pub async fn pool_remove(
    filesystem: String,
    name: String,
    ost: String,
) -> Result<(), ImlAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_remove", &pn, ost.as_str()]).await.map(drop)
}

pub async fn action_pool_remove(cmd: CmdPoolOst) -> Result<(), ImlAgentError> {
    pool_remove(cmd.filesystem, cmd.name, cmd.ost).await
}

pub async fn pool_destroy(filesystem: String, name: String) -> Result<(), ImlAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_destroy", &pn]).await.map(drop)
}

pub async fn action_pool_destroy(cmd: CmdPool) -> Result<(), ImlAgentError> {
    pool_destroy(cmd.filesystem, cmd.name).await
}

async fn pool_list(filesystem: &str) -> Result<Vec<String>, ImlAgentError> {
    match lctl(vec!["pool_list", &filesystem]).await {
        Ok(o) => Ok(String::from_utf8_lossy(&o.stdout)
            .lines()
            .skip(1)
            .map(|s| s.rsplit('.').next().unwrap().to_string())
            .collect()),
        Err(e) => {
            if let ImlAgentError::CmdOutputError(cerr) = e {
                if cerr.status.code() == Some(2) {
                    Ok(vec![])
                } else {
                    Err(ImlAgentError::CmdOutputError(cerr))
                }
            } else {
                Err(e)
            }
        }
    }
}

pub async fn pools(filesystem: String) -> Result<Vec<OstPool>, ImlAgentError> {
    let xs = pool_list(&filesystem).await?;

    let xs = xs.into_iter().map(|pool| {
        let filesystem = filesystem.clone();

        async move {
            let p = format!("{}.{}", filesystem, pool);

            let osts = { pool_list(&p) };

            Ok::<_, ImlAgentError>(OstPool {
                name: pool.to_string(),
                filesystem,
                osts: osts.await?,
            })
        }
    });

    let xs = try_join_all(xs).await?;

    Ok(xs)
}
