// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    env,
    http_comms::mailbox_client,
};
use futures::{
    future::self,
    stream, StreamExt, TryFutureExt, TryStreamExt,
};
use iml_wire_types::{FidError, FidItem};
use liblustreapi::LlapiFid;
use std::{collections::HashMap, io, path::PathBuf};
use tokio::task::spawn_blocking;
use tokio::fs;
use tracing::{error, warn};

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

async fn copy_file(llapi: LlapiFid,
		   fids: Vec<String>,
		   dest_path: &PathBuf) -> Result<(), ImlAgentError> {

    warn!("fids {:?}", fids);
    
    for fidstr in fids {
	let src_file = format!("{}/{}", llapi.mntpt(),
			       llapi.fid2path(&fidstr)?);
	let mut dest_file = PathBuf::from(dest_path);
	dest_file.push(llapi.fid2path(&fidstr)?);

	let mut dest_dir = PathBuf::from(&dest_file);
	dest_dir.pop();
    
	let result = fs::create_dir_all(&dest_dir).await;
	warn!("create {} result {:?}", dest_dir.display(), result);
    
	let resultb = fs::copy(&src_file, &dest_file).await;
    
	warn!("copied {} to {} result {:?}", &src_file, dest_file.display(),
	      resultb);
    }
    
    Ok(())
}

pub fn filesync_files(device: &str,
		      _fids: Vec<String>,
		      dest_str: String) -> Result<(), ImlAgentError> {
    let _llapi = LlapiFid::create(&device).map_err(|e| {
        error!("Failed to find rootpath({}) -> {}", device, e);
        e
    })?;
    let _dest_path: PathBuf = PathBuf::from(dest_str);

    error!("Got FileSync?");
    Ok(())
}

/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, _task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
/*    let dest_src = task_args.get("target_fs".into()).ok_or(RequiredError(
        "Task missing 'target_fs' argument".to_string(),
))?;*/
    let dest_src = "/mnt/lustre/filesync";

    let dest_path = PathBuf::from(dest_src);
    let cp_chunks = 10;

    let fids = fid_list.into_iter().map(|fi| fi.fid.clone());
    stream::iter(fids)
        .chunks(cp_chunks)
        .map(|xs| Ok::<_, ImlAgentError>(xs.into_iter().collect()))
        .try_for_each_concurrent(cp_chunks, |fids| {
	    copy_file(llapi.clone(), fids, &dest_path)
		.or_else(|e| {
		    warn!("Error copyint fid {} to {}", e, dest_src);
		    future::ok(())
		})
		.map_ok(|_| warn!("copied fid"))
	})
        .await?;

    Ok(vec![])
}
