// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate futures;
extern crate tokio;

use crate::action_plugins::stratagem::util::search_rootpath;
use crate::agent_error::{ImlAgentError, RequiredError};
use futures::TryFutureExt;
use iml_wire_types::{FidError, FidItem};
use liblustreapi::LlapiFid;
use std::io::Write;
use std::{collections::HashMap, path::PathBuf};
use tokio::fs;
use tokio::process::Command;
use tokio::task::spawn_blocking;
use tracing::{debug, error};

async fn single_fid(
    llapi: LlapiFid,
    task_args: HashMap<String, String>,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let dest = task_args
        .get("remote".into())
        .ok_or(RequiredError("Task missing 'remote' argument".to_string()))?;

    let output = Command::new("mpirun")
        .arg("--hostfile")
        .arg("/etc/iml/filesync-hostfile")
        .arg("--allow-run-as-root")
        .arg("dcp")
        .arg(format!(
            "{}/{}",
            llapi.mntpt(),
            llapi.fid2path(&fid_list[0].fid)?
        ))
        .arg(format!("{}", dest))
        .output();
    let output = output.await?;

    error!(
        "exited with {} {} {}",
        output.status,
        std::str::from_utf8(&output.stdout)?,
        std::str::from_utf8(&output.stderr)?
    );

    Ok(vec![])
}

async fn long_list(
    llapi: LlapiFid,
    task_args: HashMap<String, String>,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let dest_src = task_args
        .get("remote".into())
        .ok_or(RequiredError("Task missing 'remote' argument".to_string()))?;

    let mut tmp_workfile = PathBuf::from(dest_src);
    fs::create_dir_all(&tmp_workfile).await.or_else(|e| {
        error!("failed to create temp file: {}", e);
        return Err(e);
    })?;

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
        let dest_file = format!("{}/{}", dest_src, &fid_path);

        let mut dest_dir = PathBuf::from(&dest_file);
        dest_dir.pop();

        fs::create_dir_all(&dest_dir).await?;
        workfile.write_all(src_file.as_bytes())?;
    }

    workfile.flush()?;

    let tmpstr: String = tmp_workfile.as_path().display().to_string();

    /* dcp needs to have / on the end of the source/destination paths
     * otherwise you get /mnt/lustre/dir1/foo getting copied to
     * $DEST/lustre/dir1/foo which is ... weird
     */
    let output = Command::new("mpirun")
        .arg("--hostfile")
        .arg("/etc/iml/filesync-hostfile")
        .arg("--allow-run-as-root")
        .arg("dcp")
        .arg("-i")
        .arg(tmpstr)
        .arg(format!("{}/", llapi.mntpt()))
        .arg(format!("{}/", dest_src))
        .output();
    let output = output.await?;

    error!(
        "exited with {} {} {}",
        output.status,
        std::str::from_utf8(&output.stdout)?,
        std::str::from_utf8(&output.stderr)?
    );

    Ok(vec![])
}

/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;

    if fid_list.len() == 2 {
        return single_fid(llapi, task_args, fid_list).await;
    } else {
        return long_list(llapi, task_args, fid_list).await;
    }
}
