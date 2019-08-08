// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, http_comms::mailbox_client};
use futures::future::poll_fn;
use futures::{Future, Stream};
use liblustreapi::LlapiFid;
use tokio_threadpool::blocking;

pub fn purge_files(
    device: &str,
    fids: Vec<String>
) -> Result<(), ImlAgentError> {
    let llapi = LlapiFid::create(&device).map_err(|e| {
        log::error!("Failed to find rootpath({}) -> {}", device, e);
        ImlAgentError::LiblustreError(e)
    })?;
    llapi.rmfids(fids).map_err(ImlAgentError::LiblustreError)
}

fn search_rootpath(device: String) -> impl Future<Item = LlapiFid, Error = ImlAgentError> {
    poll_fn(move || {
        blocking(|| LlapiFid::create(&device)).map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(std::convert::identity)
    .from_err()
}

fn rm_fids(llapi: LlapiFid, fids: Vec<String>) -> impl Future<Item = (), Error = ImlAgentError> {
    poll_fn(move || {
        blocking(|| llapi.clone().rmfids(fids.clone()))
            .map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(std::convert::identity)
    .from_err()
}

pub fn read_mailbox(
    (fsname_or_mntpath, mailbox): (String, String),
) -> impl Future<Item = (), Error = ImlAgentError> {
    search_rootpath(fsname_or_mntpath).and_then(move |llapi| {
        mailbox_client::get(mailbox)
            .filter_map(|x| {
                x.trim()
                    .split(' ')
                    .filter(|x| x != &"")
                    .last()
                    .map(String::from)
            })
            .chunks(llapi.rmfids_size())
            .for_each(move |fids| {
                tokio::spawn(
                    rm_fids(llapi.clone(), fids)
                        .map_err(|e| log::warn!("Error removing fid {:?}", e)),
                );
                Ok(())
            })
    })
}
