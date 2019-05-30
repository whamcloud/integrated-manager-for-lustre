// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, fidlist, http_comms::mailbox_client};
use futures::{future::Future, stream::Stream};

pub fn purge_files(
    device: &String,
    args: impl IntoIterator<Item = String>,
) -> Result<(), ImlAgentError> {
    liblustreapi::rmfids(&device, args).map_err(ImlAgentError::LiblustreError)
}

pub fn read_mailbox(device: &str, mailbox: &str) -> Result<(), ImlAgentError> {
    let mntpt = liblustreapi::search_rootpath(&device).map_err(|e| {
        log::error!("Failed to find rootpath({}) -> {:?}", device, e);
        e
    })?;

    // Spawn off an expensive computation
    tokio::spawn(
        mailbox_client::get(mailbox.to_string())
            // @@ add multithreading here - chunking?
            .and_then(|s| serde_json::from_str(&s).map_err(ImlAgentError::Serde))
            .for_each(move |fli: fidlist::FidListItem| {
                liblustreapi::rmfid(&mntpt, &fli.fid).map_err(ImlAgentError::LiblustreError)
            })
            .map_err(|e| {
                log::error!("Failed {:?}", e);
                ()
            }),
    );

    Ok(())
}
