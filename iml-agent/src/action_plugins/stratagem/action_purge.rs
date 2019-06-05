// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, fidlist, http_comms::mailbox_client};
use futures::future::poll_fn;
use futures::{Future, Stream};
use tokio_threadpool::blocking;

pub fn purge_files(
    device: &String,
    args: impl IntoIterator<Item = String>,
) -> Result<(), ImlAgentError> {
    let mntpt = match liblustreapi::search_rootpath(&device) {
        Ok(m) => m,
        Err(e) => return Err(ImlAgentError::LiblustreError(e)),
    };
    liblustreapi::rmfids(&mntpt, args).map_err(ImlAgentError::LiblustreError)
}

fn search_rootpath(device: String) -> impl Future<Item = String, Error = ImlAgentError> {
    poll_fn(move || {
        blocking(|| liblustreapi::search_rootpath(&device))
            .map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(std::convert::identity)
    .from_err()
}

fn rm_fids(mntpt: String, fids: Vec<String>) -> impl Future<Item = (), Error = ImlAgentError> {
    poll_fn(move || {
        blocking(|| liblustreapi::rmfids(&mntpt, fids.clone()))
            .map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(std::convert::identity)
    .from_err()
}

pub fn read_mailbox(
    (device, mailbox): (String, String),
) -> impl Future<Item = (), Error = ImlAgentError> {
    search_rootpath(device).and_then(move |mntpt| {
        mailbox_client::get(mailbox)
            .and_then(|s| serde_json::from_str(&s).map_err(ImlAgentError::Serde))
            .map(|fli: fidlist::FidListItem| fli.fid)
            .chunks(10) // @@ Get number from liblustreapi
            .for_each(move |fids| {
                tokio::spawn(
                    rm_fids(mntpt.clone(), fids)
                        .map_err(|e| log::warn!("Error removing fid {:?}", e)),
                );
                Ok(())
            })
    })
}
