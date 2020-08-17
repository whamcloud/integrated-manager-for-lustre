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

/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
    let dest_src = task_args.get("remote".into()).ok_or(RequiredError(
        "Task missing 'remote' argument".to_string(),))?;

    let tmp_workfile = PathBuf::from(dest_src);
    let result = fs::create_dir_all(&tmp_workfile).await;

    tmp_workfile.push("workfile");

    let workfile = std::fs::File::create(&tmp_workfile)?;
    let mut workfile = std::io::LineWriter::new(workfile);

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
    let output = output.await?;

/*    warn!("exited with {} {} {}", output.status, std::str::from_utf8(&output.stdout)?, std::str::from_utf8(&output.stderr)?);
*/
    Ok(vec![])
}
