// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::EmfAgentError, lustre::search_rootpath};
use emf_wire_types::{FidError, FidItem};
use futures::{
    future::{self, TryFutureExt},
    stream::{self, StreamExt, TryStreamExt},
};
use liblustreapi::LlapiFid;
use std::{collections::HashMap, convert::Into};
use tokio::task::spawn_blocking;
use tracing::{debug, error, warn};

pub fn purge_files(device: &str, fids: Vec<String>) -> Result<(), EmfAgentError> {
    let llapi = LlapiFid::create(&device).map_err(|e| {
        error!("Failed to find rootpath({}) -> {}", device, e);
        e
    })?;

    llapi.rmfids(fids).map_err(Into::into)
}

async fn rm_fids(llapi: LlapiFid, fids: Vec<String>) -> Result<(), EmfAgentError> {
    spawn_blocking(move || llapi.rmfids(fids).map_err(EmfAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity)
}

pub async fn process_fids(
    (fsname_or_mntpath, _task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, EmfAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let rmfids_size = llapi.rmfids_size();

    let fids = fid_list.into_iter().map(|fi| fi.fid);
    stream::iter(fids)
        .chunks(rmfids_size)
        .map(|xs| Ok::<_, EmfAgentError>(xs.into_iter().collect()))
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
