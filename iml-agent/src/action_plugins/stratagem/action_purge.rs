// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, fidlist, http_comms::mailbox_client};
use futures::{Future, Stream};

pub fn purge_files(
    device: &String,
    args: impl IntoIterator<Item = String>,
) -> Result<(), ImlAgentError> {
    liblustreapi::rmfids(&device, args).map_err(ImlAgentError::LiblustreError)
}

pub fn read_mailbox(device: &str, mailbox: &str) -> impl Future<Item = (), Error = ImlAgentError> {
    let mntpt = match liblustreapi::search_rootpath(&device) {
        Ok(m) => m,
        Err(e) => {
            panic!("Failed to find rootpath({}) -> {:?}", device, e);
            //return futures::future::err(ImlAgentError::LiblustreError(e));
        }
    };

    mailbox_client::get(mailbox.to_string())
        .and_then(|s| serde_json::from_str(&s).map_err(ImlAgentError::Serde))
        .for_each(move |fli: fidlist::FidListItem| {
            liblustreapi::rmfid(&mntpt, &fli.fid).map_err(ImlAgentError::LiblustreError)
        })
}
