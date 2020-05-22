// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{ImlAgentError, RequiredError},
    env, fidlist,
    http_comms::mailbox_client,
};
use futures::{
    future::{self, join_all},
    sink::SinkExt,
    stream, StreamExt, TryFutureExt, TryStreamExt,
};
use iml_wire_types::FidItem;
use liblustreapi::LlapiFid;
use std::{collections::HashMap, io, path::PathBuf};
use tokio::task::spawn_blocking;
use tracing::{debug, error};

/// Runs `fid2path` on the incoming `String`.
/// Any error during `fid2path` is logged but does not return the associated Error
async fn fid2path(llapi: LlapiFid, fid: String) -> Option<String> {
    let r = spawn_blocking(move || llapi.fid2path(&fid).map_err(ImlAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity);

    match r {
        Ok(x) => Some(x),
        Err(e) => {
            error!("Could not resolve fid: {}", e);
            None
        }
    }
}

async fn search_rootpath(device: String) -> Result<LlapiFid, ImlAgentError> {
    spawn_blocking(move || LlapiFid::create(&device).map_err(ImlAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity)
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
pub async fn read_mailbox(
    (fsname_or_mntpath, mailbox): (String, String),
) -> Result<PathBuf, ImlAgentError> {
    let mut txt_path: PathBuf = PathBuf::from(env::get_var_else("REPORT_DIR", "/tmp"));
    txt_path.push(mailbox.to_string());
    txt_path.set_extension("txt");

    let f = iml_fs::file_write_bytes(txt_path.clone()).await?;

    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let mntpt = llapi.mntpt();

    mailbox_client::get(mailbox)
        .try_filter_map(|x| {
            future::ok(
                x.trim()
                    .split(' ')
                    .filter(|x| x != &"")
                    .last()
                    .map(|x| fidlist::FidListItem::new(x.into())),
            )
        })
        .chunks(1000)
        .map(|xs| -> Result<Vec<_>, _> { xs.into_iter().collect() })
        .and_then(|xs| {
            let llapi2 = llapi.clone();

            async move {
                let xs =
                    join_all(xs.into_iter().map(move |x| fid2path(llapi2.clone(), x.fid))).await;

                Ok(xs)
            }
        })
        .inspect(|_| debug!("Resolved 1000 Fids"))
        .map_ok(move |xs| {
            xs.into_iter()
                .filter_map(std::convert::identity)
                .map(|x| format!("{}/{}", mntpt, x))
                .collect()
        })
        .map_ok(|xs: Vec<String>| bytes::BytesMut::from(xs.join("\n").as_str()))
        .map_ok(|mut x: bytes::BytesMut| {
            if !x.is_empty() {
                x.extend_from_slice(b"\n");
            }
            x.freeze()
        })
        .forward(f.sink_err_into())
        .await?;

    Ok(txt_path)
}

async fn fi2path(llapi: LlapiFid, fi: FidItem) -> Option<String> {
    let pfids: Vec<fidlist::LinkEA> = serde_json::from_value(fi.data).unwrap_or(vec![]);

    let path = if let Some(pfid) = pfids.get(0) {
        format!(
            "{}/{}",
            fid2path(llapi, pfid.pfid.clone()).await?,
            pfid.name
        )
    } else {
        fid2path(llapi.clone(), fi.fid).await?
    };
    Some(path)
}

/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<(), ImlAgentError> {
    let txt_path = task_args.get("report_file".into()).ok_or(RequiredError(
        "Task missing 'report_file' argument".to_string(),
    ))?;

    let f = iml_fs::file_write_bytes(txt_path.into()).await?;

    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let mntpt = llapi.mntpt();

    stream::iter(fid_list)
        .chunks(1000)
        .map(|xs| Ok::<_, ImlAgentError>(xs.into_iter().collect()))
        .and_then(|xs: Vec<_>| {
            let llapi = llapi.clone();

            async move {
                let xs = join_all(xs.into_iter().map(move |x| fi2path(llapi.clone(), x))).await;

                Ok(xs)
            }
        })
        .inspect(|_| debug!("Resolved 1000 Fids"))
        .map_ok(move |xs| {
            xs.into_iter()
                .filter_map(std::convert::identity)
                .map(|x| format!("{}/{}", mntpt, x))
                .collect()
        })
        .map_ok(|xs: Vec<String>| bytes::BytesMut::from(xs.join("\n").as_str()))
        .map_ok(|mut x: bytes::BytesMut| {
            if !x.is_empty() {
                x.extend_from_slice(b"\n");
            }
            x.freeze()
        })
        .forward(f.sink_err_into())
        .await?;
    Ok(())
}
