// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::lctl};
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

pub fn pools(filesystem: String) -> impl Future<Item = Vec<OstPool>, Error = ImlAgentError> {
    lctl(&["pool_list", filesystem.as_str()])
        .map(|o| {
            // o.status.code() == 2 (ENOENT) is OKAY => vec![]
            String::from_utf8_lossy(&o.stdout)
                .to_string()
                .lines()
                .skip(1)
                .map(|s| s.rsplit('.').next().unwrap())
                .map(move |pool| OstPool {
                    filesystem: filesystem.clone(),
                    name: pool.to_string(),
                    osts: vec![] as Vec<String>, // @@ Do lctl "pool_list", filename.pool for these OSTs
                })
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
