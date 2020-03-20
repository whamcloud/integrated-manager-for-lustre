// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, http_comms::mailbox_client};
use futures::{
    future::{self, TryFutureExt},
    stream::{StreamExt, TryStreamExt},
};
use liblustreapi::LlapiFid;
use std::convert::Into;
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
    spawn_blocking(move || llapi.clone().rmfids(fids).map_err(ImlAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity)
}

pub async fn read_mailbox(
    (fsname_or_mntpath, mailbox): (String, String),
) -> Result<(), ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let rmfids_size = llapi.rmfids_size();

    mailbox_client::get(mailbox)
        .map_ok(|x| {
            x.trim()
                .split(' ')
                .filter(|x| !x.is_empty())
                .last()
                .map(String::from)
        })
        .try_filter_map(future::ok)
        .chunks(rmfids_size)
        .map(|xs| xs.into_iter().collect())
        .try_for_each_concurrent(10, |fids| {
            rm_fids(llapi.clone(), fids)
                .or_else(|e| {
                    warn!("Error removing fid {}", e);
                    future::ok(())
                })
                .map_ok(|_| debug!("removed {} fids", rmfids_size))
        })
        .await
}
