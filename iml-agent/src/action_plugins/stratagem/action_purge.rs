// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, http_comms::mailbox_client};
use futures::{
    compat::{Future01CompatExt, Stream01CompatExt},
    future::{self, FutureExt, TryFutureExt},
    stream::{StreamExt, TryStreamExt},
};
use futures01::{future::poll_fn, Future as Future01};
use liblustreapi::{error::LiblustreError, LlapiFid};
use std::convert::Into;
use tokio_threadpool::blocking;
use tracing::{debug, error, warn};

pub fn purge_files(device: &str, fids: Vec<String>) -> Result<(), ImlAgentError> {
    let llapi = LlapiFid::create(&device).map_err(|e| {
        error!("Failed to find rootpath({}) -> {}", device, e);
        e
    })?;

    llapi.rmfids(fids.clone()).map_err(Into::into)
}

async fn poller<T>(f: impl FnMut() -> futures01::Poll<T, tokio_threadpool::BlockingError>) -> T {
    poll_fn(f)
        .compat()
        .map_err(|_| panic!("the threadpool shut down"))
        .await
        .unwrap()
}

async fn search_rootpath(device: String) -> Result<LlapiFid, LiblustreError> {
    poller(|| blocking(|| LlapiFid::create(&device))).await
}

async fn rm_fids(llapi: LlapiFid, fids: Vec<String>) -> Result<(), LiblustreError> {
    poller(|| blocking(|| llapi.clone().rmfids(fids.clone()))).await
}

pub fn read_mailbox(x: (String, String)) -> impl Future01<Item = (), Error = ImlAgentError> {
    read_mailbox_async(x).boxed().compat()
}

pub async fn read_mailbox_async(
    (fsname_or_mntpath, mailbox): (String, String),
) -> Result<(), ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let rmfids_size = llapi.rmfids_size();

    mailbox_client::get(mailbox)
        .compat()
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
