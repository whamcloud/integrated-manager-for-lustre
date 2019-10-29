// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env, fidlist, http_comms::mailbox_client};
use futures01::{
    future::{self, join_all, poll_fn},
    Future, Sink, Stream,
};
use liblustreapi::LlapiFid;
use std::{io, path::PathBuf};
use tokio_threadpool::blocking;
use tracing::{debug, error, span, Level};
use tracing_futures::Instrument;

/// Runs `fid2path` on the incoming `String`.
/// Any error during `fid2path` is logged but does not return the associated Error
fn fid2path(
    llapi: LlapiFid,
    fid: String,
) -> impl Future<Item = Option<String>, Error = ImlAgentError> {
    poll_fn(move || {
        blocking(|| llapi.fid2path(&fid)).map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(std::convert::identity)
    .then(|r| match r {
        Ok(x) => future::ok(Some(x)),
        Err(e) => {
            error!("Could not resolve fid: {}", e);
            future::ok(None)
        }
    })
}

fn search_rootpath(device: String) -> impl Future<Item = LlapiFid, Error = ImlAgentError> {
    poll_fn(move || {
        blocking(|| LlapiFid::create(&device)).map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(std::convert::identity)
    .from_err()
}

pub fn write_records(
    device: &str,
    args: impl IntoIterator<Item = String>,
    mut wtr: impl io::Write,
) -> Result<(), ImlAgentError> {
    let llapi = LlapiFid::create(&device).map_err(|e| {
        error!("Failed to find rootpath({}) -> {}", device, e);
        e
    })?;

    for fid in args {
        let rec = llapi.fid2path(&fid)?;
        wtr.write_all(rec.as_bytes())?;
    }

    wtr.flush()?;

    Ok(())
}

/// Read mailbox and build a file of files. return pathname of generated file
pub fn read_mailbox(
    (fsname_or_mntpath, mailbox): (String, String),
) -> impl Future<Item = PathBuf, Error = ImlAgentError> {
    let mut txt_path: PathBuf = PathBuf::from(env::get_var_else("REPORT_DIR", "/tmp"));
    txt_path.push(mailbox.to_string());
    txt_path.set_extension("txt");

    let s = mailbox_client::get(mailbox)
        .filter_map(|x| {
            x.trim()
                .split(' ')
                .filter(|x| x != &"")
                .last()
                .map(|x| fidlist::FidListItem::new(x.into()))
        })
        .chunks(1000)
        .instrument(span!(Level::INFO, "Incoming fids"));

    iml_fs::file_write_bytes(txt_path.clone())
        .from_err()
        .and_then(|f| search_rootpath(fsname_or_mntpath).map(|llapi| (llapi, f)))
        .and_then(|(llapi, f)| {
            let mntpt = llapi.mntpt();

            let s2 = s
                .and_then(move |xs| {
                    let llapi2 = llapi.clone();

                    join_all(xs.into_iter().map(move |x| fid2path(llapi2.clone(), x.fid)))
                })
                .inspect(|_| debug!("Resolved 1000 Fids"))
                .map(move |xs| {
                    xs.into_iter()
                        .filter_map(std::convert::identity)
                        .map(|x| format!("{}/{}", mntpt, x))
                        .collect()
                })
                .map(|xs: Vec<String>| -> bytes::BytesMut { xs.join("\n").into() })
                .map(|mut x: bytes::BytesMut| {
                    if !x.is_empty() {
                        x.extend_from_slice(b"\n");
                    }

                    x.freeze()
                });

            f.sink_from_err().send_all(s2).map(drop)
        })
        .map(move |_| txt_path)
        .instrument(span!(Level::INFO, "Fid writer",))
}
