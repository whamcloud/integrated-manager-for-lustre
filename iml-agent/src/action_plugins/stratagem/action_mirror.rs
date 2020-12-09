// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, lustre::search_rootpath};
use futures::future::join_all;
use iml_cmd::{CheckedCommandExt, CmdError, Command};
use iml_wire_types::{FidError, FidItem};
use std::{collections::HashMap, ffi::OsStr, process::Output};

async fn lfs_mirror<S: AsRef<OsStr>>(
    args: impl IntoIterator<Item = S>,
    path: String,
) -> Result<Output, CmdError> {
    Command::new("/usr/bin/lfs")
        .arg("mirror")
        .args(args)
        .arg(path)
        .kill_on_drop(true)
        .checked_output()
        .await
}

async fn lfs_mirror_fiderror<S: AsRef<OsStr>>(
    args: impl IntoIterator<Item = S>,
    fi: &FidItem,
    mntpt: &str,
) -> Option<FidError> {
    let path = format!("{}/.lustre/fid/{}", mntpt, fi.fid);

    match lfs_mirror(args, path).await {
        Ok(output) => {
            if output.status.success() {
                None
            } else {
                Some(FidError {
                    fid: fi.fid.clone(),
                    data: fi.data.clone(),
                    errno: output.status.code().unwrap_or(0) as i16,
                })
            }
        }
        Err(CmdError::Io(err)) => Some(FidError {
            fid: fi.fid.clone(),
            data: fi.data.clone(),
            errno: err.raw_os_error().unwrap_or(-1) as i16,
        }),
        Err(CmdError::Output(err)) => {
            tracing::warn!("Fid {} returned CmdError({:?})", &fi.fid, err);
            None
        }
    }
}

/// Task Args:
/// * pool - pool to extend to
/// * striping - space seperated options to "lfs extend"
/// Fid Args: NONE
pub async fn process_extend_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
    let mntpt = llapi.mntpt();

    let pool = match task_args.get("pool") {
        Some(p) => p,
        None => return Err(ImlAgentError::MissingArgument("task::pool".into())),
    };

    let mut args = vec!["extend", "-N", "-p", pool];
    if let Some(striping) = task_args.get("striping") {
        args.extend(striping.split(' '));
    }

    let xs = fid_list.into_iter().map(|fi| {
        let mntpt = &mntpt;
        let args = &args;

        async move { lfs_mirror_fiderror(args, &fi, mntpt).await }
    });

    Ok(join_all(xs).await.into_iter().filter_map(|x| x).collect())
}

/// Task Args: NONE
/// Fid Args: NONE
pub async fn process_resync_fids(
    (fsname_or_mntpath, _task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
    let mntpt = llapi.mntpt();

    let args = vec!["resync"];

    let xs = fid_list.into_iter().map(|fi| {
        let mntpt = &mntpt;
        let args = &args;

        async move { lfs_mirror_fiderror(args, &fi, mntpt).await }
    });

    Ok(join_all(xs).await.into_iter().filter_map(|x| x).collect())
}

/// Task Args:
/// * pool - pool to remove from mirroring
/// Fid Args: NONE
pub async fn process_split_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, HashMap<String, String>, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
    let mntpt = llapi.mntpt();

    let pool = task_args.get("pool").unwrap(); // @@ - or error?

    let args = vec!["split", "-d", "-p", pool];

    let xs = fid_list.into_iter().map(|fi| {
        let mntpt = &mntpt;
        let args = &args;

        async move { lfs_mirror_fiderror(args, &fi, mntpt).await }
    });

    Ok(join_all(xs).await.into_iter().filter_map(|x| x).collect())
}
