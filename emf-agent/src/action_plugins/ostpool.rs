// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{EmfAgentError, RequiredError},
    lustre::lctl,
};
use emf_cmd::CmdError;
use emf_wire_types::OstPool;
use futures::future::try_join_all;
use std::iter::FromIterator;
use std::time::Duration;
use tokio::time::sleep;

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

pub async fn pool_create(filesystem: String, name: String) -> Result<(), EmfAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_new", &pn]).await.map(drop)
}

/// This needs to be a seperate action from pool_create() since pool create runs on MGS
/// and this runs on MDS
pub async fn action_pool_wait(cmd: CmdPool) -> Result<(), EmfAgentError> {
    let time_to_wait = 120;
    // wait up to a 2 minutes
    for _ in 0_u32..(time_to_wait * 2) {
        let pl = pool_list(&cmd.filesystem).await?;

        if pl.contains(&cmd.name) {
            return Ok(());
        }
        sleep(Duration::from_millis(500)).await;
    }

    Err(EmfAgentError::from(RequiredError(format!(
        "Waiting for pool create {}.{} failed after {} sec",
        cmd.filesystem, cmd.name, time_to_wait
    ))))
}

pub async fn action_pool_create(cmd: CmdPool) -> Result<(), EmfAgentError> {
    pool_create(cmd.filesystem, cmd.name).await
}

pub async fn pool_add(filesystem: String, name: String, ost: String) -> Result<(), EmfAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_add", &pn, ost.as_str()]).await.map(drop)
}

pub async fn action_pool_add(cmd: CmdPoolOst) -> Result<(), EmfAgentError> {
    pool_add(cmd.filesystem, cmd.name, cmd.ost).await
}

pub async fn pool_remove(
    filesystem: String,
    name: String,
    ost: String,
) -> Result<(), EmfAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_remove", &pn, ost.as_str()]).await.map(drop)
}

pub async fn action_pool_remove(cmd: CmdPoolOst) -> Result<(), EmfAgentError> {
    pool_remove(cmd.filesystem, cmd.name, cmd.ost).await
}

pub async fn pool_destroy(filesystem: String, name: String) -> Result<(), EmfAgentError> {
    let pn = format!("{}.{}", filesystem, name);
    lctl(vec!["pool_destroy", &pn]).await.map(drop)
}

pub async fn action_pool_destroy(cmd: CmdPool) -> Result<(), EmfAgentError> {
    pool_destroy(cmd.filesystem, cmd.name).await
}

pub async fn pool_list(filesystem: &str) -> Result<Vec<String>, EmfAgentError> {
    match lctl(vec!["pool_list", &filesystem]).await {
        Ok(o) => Ok(o
            .lines()
            .skip(1)
            .map(|s| s.rsplit('.').next().unwrap().to_string())
            .collect()),
        Err(e) => {
            if let EmfAgentError::CmdError(CmdError::Output(output)) = e {
                if output.status.code() == Some(2) {
                    Ok(vec![])
                } else {
                    Err(output.into())
                }
            } else {
                Err(e)
            }
        }
    }
}

pub async fn ost_list<B>(filesystem: &str, pool: &str) -> Result<B, EmfAgentError>
where
    B: FromIterator<String>,
{
    let pn = format!("{}.{}", filesystem, pool);
    pool_list(&pn).await.map(|l| {
        l.iter()
            .map(|s| s.trim_end_matches("_UUID").to_string())
            .collect()
    })
}

pub async fn pools(filesystem: String) -> Result<Vec<OstPool>, EmfAgentError> {
    let xs = pool_list(&filesystem).await?;

    let xs = xs.into_iter().map(|pool| {
        let filesystem = &filesystem;

        async move {
            let osts = ost_list(&filesystem, &pool);

            Ok::<_, EmfAgentError>(OstPool {
                name: pool.to_string(),
                filesystem: filesystem.clone(),
                osts: osts.await?,
            })
        }
    });

    let xs = try_join_all(xs).await?;

    Ok(xs)
}
