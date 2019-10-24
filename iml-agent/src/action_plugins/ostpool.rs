// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::lctl};
use futures::{
    compat::Future01CompatExt,
    future::try_join_all,
    future::{FutureExt, TryFutureExt},
};
use futures01::Future;
use iml_wire_types::OstPool;

pub fn pool_create(
    filesystem: String,
    name: String,
) -> impl Future<Item = (), Error = ImlAgentError> {
    lctl(&["pool_new", format!("{}.{}", filesystem, name).as_str()]).map(drop)
}

pub fn pool_add(
    filesystem: String,
    name: String,
    ost: String,
) -> impl Future<Item = (), Error = ImlAgentError> {
    lctl(&[
        "pool_add",
        format!("{}.{}", filesystem, name).as_str(),
        ost.as_str(),
    ])
    .map(drop)
}

pub fn pool_remove(
    filesystem: String,
    name: String,
    ost: String,
) -> impl Future<Item = (), Error = ImlAgentError> {
    lctl(&[
        "pool_remove",
        format!("{}.{}", filesystem, name).as_str(),
        ost.as_str(),
    ])
    .map(drop)
}

pub fn pool_destroy(
    filesystem: String,
    name: String,
) -> impl Future<Item = (), Error = ImlAgentError> {
    lctl(&["pool_destroy", format!("{}.{}", filesystem, name).as_str()]).map(drop)
}

async fn pool_list(filesystem: &str) -> Result<Vec<String>, ImlAgentError> {
    lctl(&["pool_list", &filesystem])
        .compat()
        .await
        .map(|o| {
            String::from_utf8_lossy(&o.stdout)
                .lines()
                .skip(1)
                .map(|s| s.rsplit('.').next().unwrap().to_string())
                .collect()
        })
        .or_else(|e| {
            if let ImlAgentError::CmdOutputError(cerr) = e {
                if cerr.status.code() == Some(2) {
                    Ok(vec![])
                } else {
                    Err(ImlAgentError::CmdOutputError(cerr))
                }
            } else {
                Err(e)
            }
        })
}

pub async fn pools_async(filesystem: String) -> Result<Vec<OstPool>, ImlAgentError> {
    let xs = pool_list(&filesystem).await?;

    let xs = xs.into_iter().map(|pool| {
        let filesystem = filesystem.clone();

        async move {
            let p = format!("{}.{}", filesystem, pool);

            let osts = {
                pool_list(&p)
            };

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

pub fn pools(x: String) -> impl Future<Item = Vec<OstPool>, Error = ImlAgentError> {
    pools_async(x).boxed().compat()
}
