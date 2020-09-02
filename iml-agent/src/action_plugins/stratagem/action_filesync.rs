// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate futures;
extern crate tokio;

use crate::agent_error::{ImlAgentError, RequiredError};
use crate::lustre::search_rootpath;
use iml_wire_types::{FidError, FidItem};
use liblustreapi::LlapiFid;
use std::{collections::HashMap, path::PathBuf};
use tokio::fs;
use tokio::process::Command;

async fn archive_fids(
    llapi: LlapiFid,
    dest_src: &String,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let mut result = Vec::new();

    for fid in fid_list {
        let fid_path = llapi.fid2path(&fid.fid)?;
        let src_file = format!("{}/{}", llapi.mntpt(), &fid_path);
        let dest_file = format!("{}/{}", &dest_src, &fid_path);
        let mut dest_dir = PathBuf::from(&dest_file);

        dest_dir.pop();
        fs::create_dir_all(&dest_dir).await?;
        let md = fs::metadata(&src_file).await?;
        /* invoking mpifileutils is slow, so only do it for directories
         * and big files, otherwise just use rsync
         */
        let output;
        if md.is_dir() || (md.len() > 1024 * 1024 * 1024) {
            output = Command::new("/usr/lib64/openmpi/bin/mpirun")
                .arg("--hostfile")
                .arg("/etc/iml/filesync-hostfile")
                .arg("--allow-run-as-root")
                .arg("dsync")
                .arg("-S")
                .arg(src_file)
                .arg(dest_file)
                .output();
        } else {
            output = Command::new("rsync").arg(src_file).arg(dest_file).output();
        }
        let output = output.await?;

	/*tracing::error!(
            "exited with {} {} {}",
            output.status,
            std::str::from_utf8(&output.stdout)?,
            std::str::from_utf8(&output.stderr)?
        );*/

        let res = FidError {
            fid: fid.fid.clone(),
            data: fid.data.clone(),
            errno: output.status.code().unwrap_or(0) as i16,
        };
        result.push(res);
    }

    Ok(result)
}

async fn restore_fids(
    llapi: LlapiFid,
    dest_src: &String,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let mut result = Vec::new();

    for fid in fid_list {
        let fid_path = llapi.fid2path(&fid.fid)?;
        let src_file = format!("{}/{}", llapi.mntpt(), &fid_path);
        let dest_file = format!("{}/{}", &dest_src, &fid_path);
        let mut dest_dir = PathBuf::from(&src_file);

        dest_dir.pop();
        fs::create_dir_all(&dest_dir).await?;

        let md = fs::metadata(&dest_file).await?;
        /* invoking mpifileutils is slow, so only do it for directories
         * and big files, otherwise just use rsync
         */
        let output;
        if md.is_dir() || (md.len() > 1024 * 1024 * 1024) {
            output = Command::new("mpirun")
                .arg("--hostfile")
                .arg("/etc/iml/filesync-hostfile")
                .arg("--allow-run-as-root")
                .arg("dsync")
                .arg("-S")
                .arg(dest_file)
                .arg(src_file)
                .output();
        } else {
            output = Command::new("rsync").arg(dest_file).arg(src_file).output();
        }

        let output = output.await?;

        let res = FidError {
            fid: fid.fid.clone(),
            data: fid.data.clone(),
            errno: output.status.code().unwrap_or(0) as i16,
        };
        result.push(res);

        /*error!(
            "exited with {} {} {}",
            output.status,
            std::str::from_utf8(&output.stdout)?,
            std::str::from_utf8(&output.stderr)?
        );*/
    }

    Ok(result)
}

/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let dest_path = task_args
        .get("remote".into())
        .ok_or(RequiredError("Task missing 'remote' argument".to_string()))?;

    let action_name = task_args
        .get("action".into())
        .ok_or(RequiredError("Task missing 'action' argument".to_string()))?;

    // fuck it, panic.  I can'd figure out how to return an error from a match
    // statement, but I can above.
    match action_name.as_str() {
        "push" => archive_fids(llapi.clone(), dest_path, fid_list).await,
        "pull" => restore_fids(llapi.clone(), dest_path, fid_list).await,
        _ => panic!(),
    }
}
