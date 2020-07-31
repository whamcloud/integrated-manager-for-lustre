// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate futures;
extern crate tokio;

use crate::{
    agent_error::{ImlAgentError, RequiredError},
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
use tokio::process::Command;
use futures::Future;
use tracing::{error, warn};
use std::fs::File;
use std::io::{BufWriter, Write};

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
    (fsname_or_mntpath, task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
    let dest_src = task_args.get("remote".into()).ok_or(RequiredError(
        "Task missing 'remote' argument".to_string(),
))?;

    let mut tmp_workfile = PathBuf::from(dest_src);
    warn!("yam");
    /*let cp_chunks = 10;

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
     */

    let result = fs::create_dir_all(&tmp_workfile).await;
    tmp_workfile.push("workfile");
    warn!("yam1");
    let workfile = std::fs::File::create(&tmp_workfile)?;
    let mut workfile = std::io::LineWriter::new(workfile);
    warn!("yam2");

    /*
     * mpifileutils *should* create dirs, but it doesn't.
     * so create them here while we're filling out the list of things to copy
     */
    
    for fid in fid_list {
	let fid_path = llapi.fid2path(&fid.fid)?;
	let src_file = format!("{}/{}\n", llapi.mntpt(), &fid_path);
	let dest_file = format!("{}/{}",
				dest_src, &fid_path);

	let mut dest_dir = PathBuf::from(&dest_file);
	dest_dir.pop();

	let result = fs::create_dir_all(&dest_dir).await;
	workfile.write_all(src_file.as_bytes())?;
    }

    workfile.flush();
    
    let tmpstr: String = tmp_workfile.as_path().display().to_string();
    warn!("workfile: {} llapi_mntpt: {} dest_src: {}",
	  tmpstr,
	  llapi.mntpt(),
	  dest_src);

    /* dcp needs to have / on the end of the source/destination paths
     * otherwise you get /mnt/lustre/dir1/foo getting copied to
     * $DEST/lustre/dir1/foo which is ... weird
     */
    let output = Command::new("/usr/lib64/openmpi/bin/mpirun")
	.arg("--hostfile")
	.arg("/etc/iml/filesync-hostfile")
	.arg("--allow-run-as-root")
	.arg("/usr/local/bin/dcp")
	.arg("-i")
	.arg(tmpstr)
	.arg(format!("{}/", llapi.mntpt()))
	.arg(format!("{}/", dest_src))
	.output();
/*    let output = Command::new("echo").arg("hello").arg("world").output();
*/
    let output = output.await?;
    
    warn!("exited with {} {} {}", output.status, std::str::from_utf8(&output.stdout)?, std::str::from_utf8(&output.stderr)?);

    Ok(vec![])
}
