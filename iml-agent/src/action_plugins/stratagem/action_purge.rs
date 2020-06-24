// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::{
    future::{self, TryFutureExt},
    stream::{self, StreamExt, TryStreamExt},
};
use iml_wire_types::{FidError, FidItem};
use liblustreapi::LlapiFid;
use std::{collections::HashMap, convert::Into};
use tokio::task::spawn_blocking;
use tracing::{debug, error, warn};

pub fn purge_files(device: &str, fids: Vec<String>) -> Result<(), ImlAgentError> {
    let llapi = LlapiFid::create(&device).map_err(|e| {
        error!("Failed to find rootpath({}) -> {}", device, e);
        e
    })?;

    llapi.rmfids(fids).map_err(Into::into)
}

async fn search_rootpath(device: String) -> Result<LlapiFid, ImlAgentError> {
    spawn_blocking(move || LlapiFid::create(&device).map_err(ImlAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity)
}

async fn rm_fids(llapi: LlapiFid, fids: Vec<String>) -> Result<(), ImlAgentError> {
    spawn_blocking(move || llapi.rmfids(fids).map_err(ImlAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity)
}

pub async fn process_fids(
    (fsname_or_mntpath, _task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let rmfids_size = llapi.rmfids_size();

    let fids = fid_list.into_iter().map(|fi| fi.fid);
    stream::iter(fids)
        .chunks(rmfids_size)
        .map(|xs| Ok::<_, ImlAgentError>(xs.into_iter().collect()))
        .try_for_each_concurrent(10, |fids| {
            rm_fids(llapi.clone(), fids)
                .or_else(|e| {
                    warn!("Error removing fid {}", e);
                    future::ok(())
                })
                .map_ok(|_| debug!("removed {} fids", rmfids_size))
        })
        .await?;
    Ok(vec![])
}
