// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{EmfAgentError, RequiredError},
    fidlist,
    http_comms::streaming_client::send,
    lustre::search_rootpath,
};
use emf_wire_types::{FidError, FidItem};
use futures::{
    channel::mpsc, future::join_all, sink::SinkExt, stream, StreamExt, TryFutureExt, TryStreamExt,
};
use liblustreapi::LlapiFid;
use std::{collections::HashMap, io};
use tokio::task::spawn_blocking;
use tracing::{debug, error};

/// Runs `fid2path` on the incoming `String`.
/// Any error during `fid2path` is logged but does not return the associated Error
async fn fid2path(llapi: LlapiFid, fid: String) -> Option<String> {
    let r = spawn_blocking(move || llapi.fid2path(&fid).map_err(EmfAgentError::from))
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

async fn item2path(
    llapi: LlapiFid,
    fi: FidItem,
    mut tx: mpsc::UnboundedSender<FidError>,
) -> Option<String> {
    let pfids: Vec<fidlist::LinkEA> = serde_json::from_value(fi.data.clone()).unwrap_or_default();

    for pfid in pfids.iter() {
        if let Some(path) = fid2path(llapi.clone(), pfid.pfid.clone()).await {
            return Some(format!("{}/{}", path, pfid.name));
        }
    }

    if let Some(path) = fid2path(llapi.clone(), fi.fid.clone()).await {
        Some(path)
    } else {
        let _rc = tx
            .send(FidError {
                fid: fi.fid.clone(),
                data: fi.data.clone(),
                errno: 2,
            })
            .await;

        None
    }
}

pub fn write_records(
    device: &str,
    args: impl IntoIterator<Item = String>,
    mut wtr: impl io::Write,
) -> Result<(), EmfAgentError> {
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

/// Process FIDs
/// Task Args:
/// * report_file - output location of file list
/// Fid Args:
/// * pfid list - (optional) Array of LinkEA info (specifically "pfid" - parent fid)
pub async fn process_fids(
    (fsname_or_mntpath, mut task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, EmfAgentError> {
    let report_name = task_args
        .remove("report_name")
        .ok_or_else(|| RequiredError("Task missing 'report_name' argument".to_string()))?;

    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let mntpt = llapi.mntpt();

    let (tx, rx) = mpsc::unbounded::<FidError>();

    let s = stream::iter(fid_list)
        .chunks(1000)
        .map(|xs| Ok::<_, EmfAgentError>(xs.into_iter().collect()))
        .and_then(move |xs: Vec<_>| {
            let llapi = llapi.clone();
            let tx = tx.clone();
            async move {
                let xs = join_all(
                    xs.into_iter()
                        .map(move |x| item2path(llapi.clone(), x, tx.clone())),
                )
                .await;

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
        });

    tokio::spawn(send("report", report_name, s));

    Ok(rx.collect().await)
}
