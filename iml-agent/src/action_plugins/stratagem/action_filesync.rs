// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env, lustre::search_rootpath};
use futures::{future::try_join_all, future::Future, stream, StreamExt, TryStreamExt};
use iml_wire_types::{FidError, FidItem};
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
    work_list: &'a [Work],
) -> impl Future<Output = Result<Vec<FidError>, ImlAgentError>> + 'a {
    stream::iter(work_list)
        .map(move |work| async move {
            let src_file = format!("{}/{}", src_root.display(), work.file_path.display());
            let dest_file = format!("{}/{}", dest_root.display(), work.file_path.display());
            let mut dest_dir = PathBuf::from(&src_file);
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
                src_file,
                dest_file,
                output.status.code()
            );

            Ok::<_, ImlAgentError>(FidError {
                fid: work.fid.fid.clone(),
                data: work.fid.data.clone(),
                errno: output.status.code().unwrap_or(1) as i16,
            })
        })
        .chunks(10)
        .map(Ok)
        .try_fold(vec![], |mut acc, xs| async {
            let mut xs = try_join_all(xs).await?;

            xs.retain(|x| x.errno != 0);
            acc.extend(xs);

            Ok::<_, ImlAgentError>(acc)
        })
}

fn do_dsync<'a>(
    src_root: &'a PathBuf,
    dest_root: &'a PathBuf,
    work_list: &'a [Work],
) -> impl Future<Output = Result<Vec<FidError>, ImlAgentError>> + 'a {
    stream::iter(work_list)
        .map(move |work| async move {
            let mpi_path = format!("{}/mpirun", env::get_openmpi_path());
            let mpi_count = env::get_openmpi_count();
            let src_file = format!("{}/{}", src_root.display(), work.file_path.display());
            let dest_file = format!("{}/{}", dest_root.display(), work.file_path.display());

            let mut dest_dir = PathBuf::from(&src_file);
            dest_dir.pop();
            fs::create_dir_all(&dest_dir).await?;

            let output = Command::new(mpi_path)
                .arg("--allow-run-as-root")
                .arg("-c")
                .arg(format!("{}", mpi_count))
                .arg("--hostfile")
                .arg("/etc/iml/filesync-hostfile")
                .arg("dsync")
                .arg("-S")
                .arg(&src_file)
                .arg(&dest_file)
                .kill_on_drop(true)
                .output()
                .await?;

            tracing::debug!(
                " moved {} to {} {:?}",
                src_file,
                dest_file,
                output.status.code()
            );

            Ok::<_, ImlAgentError>(FidError {
                fid: work.fid.fid.clone(),
                data: work.fid.data.clone(),
                errno: output.status.code().unwrap_or(1) as i16,
            })
        })
        .chunks(1)
        .map(Ok)
        .try_fold(vec![], |mut acc, xs| async {
            let mut xs = try_join_all(xs).await?;

            xs.retain(|x| x.errno != 0);
            acc.extend(xs);

            Ok::<_, ImlAgentError>(acc)
        })
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
    let mut rsync_list: Vec<Work> = vec![];
    let mut dsync_list: Vec<Work> = vec![];
    let mut result = vec![];

    let src_root: PathBuf;
    let dest_root: PathBuf;
    if task_args.action == ActionType::Push {
        src_root = llapi.mntpt().into();
        dest_root = task_args.remote.into();
    } else {
        src_root = task_args.remote.into();
        dest_root = llapi.mntpt().into();
    }

    for fid in fid_list {
        let fid_path = match llapi.fid2path(&fid.fid) {
            Ok(x) => x,
            Err(_) => {
                tracing::error!("llapi: failed on fid {}", &fid.fid);
                continue;
            }
        };
        let src_file = format!("{}/{}", &src_root.display(), fid_path);
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
    let mut res = do_rsync(&src_root, &dest_root, &rsync_list).await?;
    result.append(&mut res);
    res.clear();
    res = do_dsync(&src_root, &dest_root, &dsync_list).await?;
    result.append(&mut res);
    res.clear();

    Ok(result)
}

pub async fn process_files(
    (fsname_or_mntpath, task_args, file_list): (PathBuf, TaskArgs, Vec<PathBuf>),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath.into_os_string().into_string().unwrap()).await?;
    let mut rsync_list: Vec<Work> = vec![];
    let mut dsync_list: Vec<Work> = vec![];
    let mut result = vec![];

    let src_root: PathBuf;
    let dest_root: PathBuf;
    if task_args.action == ActionType::Push {
        src_root = llapi.mntpt().into();
        dest_root = task_args.remote.into();
    } else {
        src_root = task_args.remote.into();
        dest_root = llapi.mntpt().into();
    }

    for file_path in file_list {
        let fidstr = match llapi.path2fid(&file_path) {
            Ok(x) => x,
            Err(_) => "[0x0:0x0:0x0]".to_string(),
        };
        let md = fs::metadata(&file_path).await?;
        file_path.strip_prefix(llapi.mntpt()).unwrap();
        let work = Work {
            file_path,
            fid: FidItem {
                fid: fidstr.clone(),
                data: fidstr.into(),
            },
        };
        if md.is_dir() || (md.len() > LARGEFILE) {
            dsync_list.push(work);
        } else {
            rsync_list.push(work);
        }
    }
    let mut res = do_rsync(&src_root, &dest_root, &rsync_list).await?;
    result.append(&mut res);
    res.clear();
    res = do_dsync(&src_root, &dest_root, &dsync_list).await?;
    result.append(&mut res);
    res.clear();

    Ok(result)
}
