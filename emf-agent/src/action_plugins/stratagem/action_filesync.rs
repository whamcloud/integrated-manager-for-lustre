// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::EmfAgentError, env, lustre::search_rootpath};
use emf_wire_types::{FidError, FidItem};
use futures::{future, future::try_join_all, future::Future, stream, StreamExt, TryStreamExt};
use std::path::PathBuf;
use structopt::clap::arg_enum;
use tokio::{fs, process::Command};

arg_enum! {
    #[derive(Debug, serde::Deserialize, Clone, Copy, PartialEq)]
    pub enum ActionType {
    Push,
    Pull,
    }

}
struct Work {
    file_path: PathBuf,
    fid: FidItem,
}

const LARGEFILE: u64 = 1024 * 1024 * 1024;

fn do_rsync<'a>(
    src_root: &'a PathBuf,
    dest_root: &'a PathBuf,
    work_list: Vec<Work>,
) -> impl Future<Output = Result<Vec<FidError>, EmfAgentError>> + 'a {
    stream::iter(work_list)
        .map(
            move |Work {
                      file_path,
                      fid: FidItem { fid, data },
                  }| async move {
                let src_file = src_root.join(&file_path);
                let dest_file = dest_root.join(&file_path);
                let mut dest_dir = PathBuf::from(&dest_file);
                dest_dir.pop();
                fs::create_dir_all(&dest_dir).await?;

                let output = Command::new("rsync")
                    .arg("-a")
                    .arg("-t")
                    .arg(&src_file)
                    .arg(&dest_file)
                    .kill_on_drop(true)
                    .output()
                    .await?;

                tracing::debug!(
                    " moved {} to {} {:?}",
                    src_file.display(),
                    dest_file.display(),
                    output.status.code()
                );

                Ok::<_, EmfAgentError>(FidError {
                    fid,
                    data,
                    errno: output.status.code().unwrap_or(1) as i16,
                })
            },
        )
        .chunks(10)
        .map(Ok)
        .try_fold(vec![], |mut acc, xs| async {
            let mut xs = try_join_all(xs).await?;

            xs.retain(|x| x.errno != 0);
            acc.extend(xs);

            Ok::<_, EmfAgentError>(acc)
        })
}

fn do_dsync<'a>(
    src_root: &'a PathBuf,
    dest_root: &'a PathBuf,
    work_list: Vec<Work>,
) -> impl Future<Output = Result<Vec<FidError>, EmfAgentError>> + 'a {
    stream::iter(work_list)
        .map(Ok)
        .and_then(
            move |Work {
                      file_path,
                      fid: FidItem { fid, data },
                  }| async move {
                let mpi_path = format!("{}/mpirun", env::get_openmpi_path());
                let mpi_count = env::get_openmpi_count();
                let src_file = src_root.join(&file_path);
                let dest_file = dest_root.join(&file_path);
                let mut dest_dir = PathBuf::from(&dest_file);
                dest_dir.pop();
                fs::create_dir_all(&dest_dir).await?;

                let output = Command::new(mpi_path)
                    .arg("--allow-run-as-root")
                    .arg("-c")
                    .arg(format!("{}", mpi_count))
                    .arg("--hostfile")
                    .arg("/etc/emf/filesync-hostfile")
                    .arg("dsync")
                    .arg("-S")
                    .arg(&src_file)
                    .arg(&dest_file)
                    .kill_on_drop(true)
                    .output()
                    .await?;

                tracing::debug!(
                    " moved {} to {} {:?}",
                    src_file.display(),
                    dest_file.display(),
                    output.status.code()
                );

                Ok::<_, EmfAgentError>(FidError {
                    fid,
                    data,
                    errno: output.status.code().unwrap_or(1) as i16,
                })
            },
        )
        .try_filter(|x| future::ready(x.errno != 0))
        .try_collect()
}

#[derive(Debug, serde::Deserialize)]
pub struct TaskArgs {
    pub remote: String,
    pub action: ActionType,
}

/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, task_args, fid_list): (String, TaskArgs, Vec<FidItem>),
) -> Result<Vec<FidError>, EmfAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;
    let mut rsync_list: Vec<Work> = vec![];
    let mut dsync_list: Vec<Work> = vec![];
    let mut result = vec![];

    let (src_root, dest_root): (PathBuf, PathBuf) = if task_args.action == ActionType::Push {
        (llapi.mntpt().into(), task_args.remote.into())
    } else {
        (task_args.remote.into(), llapi.mntpt().into())
    };

    for fid in fid_list {
        let fid_path = match llapi.fid2path(&fid.fid) {
            Ok(x) => x,
            Err(e) => {
                tracing::error!("llapi: failed on fid {}: {}", &fid.fid, e);
                continue;
            }
        };
        let src_file = src_root.join(&fid_path);
        let md = fs::metadata(&src_file).await?;
        let work = Work {
            file_path: fid_path.into(),
            fid,
        };
        if md.is_dir() || (md.len() > LARGEFILE) {
            dsync_list.push(work);
        } else {
            rsync_list.push(work);
        }
    }
    let mut res = do_rsync(&src_root, &dest_root, rsync_list).await?;
    result.append(&mut res);
    res.clear();
    res = do_dsync(&src_root, &dest_root, dsync_list).await?;
    result.append(&mut res);
    res.clear();

    Ok(result)
}
