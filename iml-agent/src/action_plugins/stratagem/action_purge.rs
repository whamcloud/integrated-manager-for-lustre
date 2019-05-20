// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env, http_comms::crypto_client};
use futures::future::Future;
use futures::stream::Stream;

pub fn purge_files(
    device: &str,
    args: impl IntoIterator<Item = String>,
) -> Result<(), ImlAgentError> {
    liblustreapi::rmfids(&device, args).map_err(ImlAgentError::LiblustreError)
}

pub fn read_mailbox(device: &str, mailbox: &str) -> Result<(), ImlAgentError> {
    let mntpt = liblustreapi::search_rootpath(&device).map_err(|e| {
        log::error!("Failed to find rootpath({}) -> {:?}", device, e);
        e
    })?;

    let query: Vec<(String, String)> = Vec::new();
    let message_endpoint = env::MANAGER_URL.join("/mailbox/")?.join(mailbox)?;
    let identity = crypto_client::get_id(&env::PFX)?;
    let client = crypto_client::create_client(identity)?;

    // Spawn off an expensive computation
    tokio::spawn(
        stream_lines::strings(crypto_client::get_stream(&client, message_endpoint, &query))
            // @@ add multithreading here - chunking?
            // @@ .map json -> fid
            .for_each(move |fid| {
                liblustreapi::rmfid(&mntpt, &fid).map_err(ImlAgentError::LiblustreError)
            })
            .map_err(|e| {
                log::error!("Failed {:?}", e);
                ()
            }),
    );

    Ok(())
}
