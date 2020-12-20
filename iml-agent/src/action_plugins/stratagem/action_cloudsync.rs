// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, lustre::search_rootpath};
use futures::{future::try_join_all, stream, StreamExt, TryStreamExt};
use iml_wire_types::{FidError, FidItem};
use liblustreapi::LlapiFid;
use structopt::clap::arg_enum;
use tokio::process::Command;

fn get_unique(input: &str) -> String {
    let str = input.replace('_', "__");
    str.replace('/', "_")
}

async fn archive_fids(
    llapi: LlapiFid,
    target_name: &str,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    stream::iter(fid_list)
        .map(|fid| {
            let fid_path = llapi.fid2path(&fid.fid);
            let mnt_pnt = llapi.mntpt();

            async move {
                let errno: i16;

                if fid_path.is_err() {
                    tracing::error!("llapi: failed on fid {}", &fid.fid);
                    errno = 2; //ENOENT
                } else {
                    let fid_path = fid_path?;
                    let src_file = format!("{}/{}", mnt_pnt, &fid_path);
                    let output = Command::new("stgm_cloudsync")
                        .arg("push")
                        .arg(src_file)
                        .arg(format!("{}:{}", target_name, get_unique(&fid_path)))
                        .kill_on_drop(true)
                        .output()
                        .await?;

                    errno = output.status.code().unwrap_or(0) as i16;
                }
                let FidItem { fid, data } = fid;
                Ok::<_, ImlAgentError>(FidError { fid, data, errno })
            }
        })
        .chunks(10)
        .map(Ok)
        .try_fold(vec![], |mut acc, xs| async {
            let mut xs = try_join_all(xs).await?;

            xs.retain(|x| x.errno != 0);
            acc.extend(xs);

            Ok::<_, ImlAgentError>(acc)
        })
        .await
}

async fn restore_fids(
    llapi: LlapiFid,
    target_name: &str,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    stream::iter(fid_list)
        .map(|fid| {
            let fid_path = llapi.fid2path(&fid.fid);
            let mnt_pnt = llapi.mntpt();

            async move {
                let errno: i16;

                if fid_path.is_err() {
                    tracing::error!("llapi: failed on fid {}", &fid.fid);
                    errno = 2; //ENOENT
                } else {
                    let fid_path = fid_path?;
                    let src_file = format!("{}/{}", mnt_pnt, &fid_path);
                    let output = Command::new("stgm_cloudsync")
                        .arg("pull")
                        .arg(format!("{}:{}", target_name, get_unique(&fid_path)))
                        .arg(src_file)
                        .kill_on_drop(true)
                        .output()
                        .await?;

                    errno = output.status.code().unwrap_or(0) as i16;
                }
                let FidItem { fid, data } = fid;
                Ok::<_, ImlAgentError>(FidError { fid, data, errno })
            }
        })
        .chunks(10)
        .map(Ok)
        .try_fold(vec![], |mut acc, xs| async {
            let mut xs = try_join_all(xs).await?;

            xs.retain(|x| x.errno != 0);
            acc.extend(xs);

            Ok::<_, ImlAgentError>(acc)
        })
        .await
}

arg_enum! {
    #[derive(Debug, serde::Deserialize, Clone, Copy)]
    pub enum ActionType {
    Push,
    Pull,
    }
}

#[derive(Debug, serde::Deserialize)]
pub struct TaskArgs {
    pub remote: String,
    pub action: ActionType,
}
/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, TaskArgs, Vec<FidItem>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
    match task_args.action {
        ActionType::Push => archive_fids(llapi.clone(), &task_args.remote, fid_list).await,
        ActionType::Pull => restore_fids(llapi.clone(), &task_args.remote, fid_list).await,
    }
}
