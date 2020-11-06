// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env, lustre::search_rootpath};
use futures::{future::try_join_all, future::Future, stream, StreamExt, TryStreamExt};
use iml_wire_types::{FidError, FidItem};
use liblustreapi::LlapiFid;
use std::path::PathBuf;
use structopt::clap::arg_enum;
use tokio::{fs, process::Command};

struct Work {
    fid: FidItem,
    src_file: String,
    dest_file: String,
}

const LARGEFILE: u64 = 1024 * 1024 * 1024;

fn do_rsync<'a>(
    work_list: &'a [Work],
) -> impl Future<Output = Result<Vec<FidError>, ImlAgentError>> + 'a {
    stream::iter(work_list)
        .map(|work| async move {
            let output = Command::new("rsync")
                .arg("-a")
                .arg("-t")
                .arg(&work.src_file)
                .arg(&work.dest_file)
                .kill_on_drop(true)
                .output()
                .await?;

            tracing::error!(
                " moved {} to {} {:?}",
                work.src_file,
                work.dest_file,
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

async fn archive_fids(
    llapi: LlapiFid,
    dest_src: &str,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let mut result = vec![];

    let mut rsync_list: Vec<Work> = vec![];
    let mpi_path = format!("{}/mpirun", env::get_openmpi_path());
    let mpi_count = env::get_openmpi_count();

    for fid in fid_list {
        let fid_path = match llapi.fid2path(&fid.fid) {
            Ok(x) => x,
            Err(_) => {
                tracing::error!("llapi: failed on fid {}", &fid.fid);
                continue;
            }
        };

        let src_file = format!("{}/{}", llapi.mntpt(), &fid_path);
        let dest_file = format!("{}/{}", &dest_src, &fid_path);
        let mut dest_dir = PathBuf::from(&dest_file);

        dest_dir.pop();
        if !dest_dir.is_dir() {
            fs::create_dir_all(&dest_dir).await?;
        }

        let md = fs::metadata(&src_file).await?;
        /* invoking mpifileutils is slow, so only do it for directories
         * and big files, otherwise just use rsync
         */
        if md.is_dir() || (md.len() > LARGEFILE) {
            let output = Command::new(&mpi_path)
                .arg("--allow-run-as-root")
                .arg("-c")
                .arg(format!("{}", mpi_count))
                .arg("--hostfile")
                .arg("/etc/iml/filesync-hostfile")
                .arg("dsync")
                .arg("-S")
                .arg(src_file)
                .arg(dest_file)
                .kill_on_drop(true)
                .output()
                .await?;

            if !output.status.success() {
                let FidItem { fid, data } = fid;
                result.push(FidError {
                    fid,
                    data,
                    errno: output.status.code().unwrap_or(1) as i16,
                });
            }
            tracing::debug!(
                "dsync exited with {} {} {}",
                output.status,
                std::str::from_utf8(&output.stdout)?,
                std::str::from_utf8(&output.stderr)?
            );
        } else {
            rsync_list.push(Work {
                fid,
                src_file,
                dest_file,
            });

            if rsync_list.len() >= 500 {
                let mut rsync_res = do_rsync(&rsync_list).await?;

                result.append(&mut rsync_res);
                rsync_res.clear();
                rsync_list.clear();
            }
        }
    }

    let mut rsync_res = do_rsync(&rsync_list).await?;

    result.append(&mut rsync_res);

    Ok(result)
}

async fn archive_files(
    dest_src: &str,
    lustre_root: PathBuf,
    file_list: Vec<PathBuf>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let result = vec![];
    tracing::error!(
        "archive files dest {} lustre {:?} list {:?}",
        &dest_src,
        lustre_root,
        file_list
    );
    Ok(result)
}

async fn restore_files(
    dest_src: &str,
    _lustre_root: PathBuf,
    file_list: Vec<PathBuf>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let mut result = vec![];
    let mpi_path = format!("{}/mpirun", env::get_openmpi_path());
    let mpi_count = env::get_openmpi_count();
    let mut rsync_list: Vec<Work> = vec![];
    let llapi = search_rootpath(dest_src.to_string()).await?;

    for src_file in file_list {
        let dest_file = format!("{}/{}", &dest_src, src_file.display());
        let mut dest_dir = PathBuf::from(&dest_file);

        tracing::error!("sync {} {}", src_file.display(), dest_file);

        dest_dir.pop();
        if !dest_dir.is_dir() {
            fs::create_dir_all(&dest_dir).await?;
        }

        let md = fs::metadata(&src_file).await?;
        /* invoking mpifileutils is slow, so only do it for directories
         * and big files, otherwise just use rsync
         */
        if md.is_dir() || (md.len() > LARGEFILE) {
            let output = Command::new(&mpi_path)
                .arg("--allow-run-as-root")
                .arg("-c")
                .arg(format!("{}", mpi_count))
                .arg("--hostfile")
                .arg("/etc/iml/filesync-hostfile")
                .arg("dsync")
                .arg("-S")
                .arg(src_file)
                .arg(&dest_file)
                .output()
                .await?;

            if !output.status.success() {
                let fid = llapi.path2fid(&PathBuf::from(&dest_file))?;
                result.push(FidError {
                    fid: fid.clone(),
                    data: fid.into(),
                    errno: output.status.code().unwrap_or(1) as i16,
                });
            }
            tracing::error!(
                "dsync exited with {} {} {}",
                output.status,
                std::str::from_utf8(&output.stdout)?,
                std::str::from_utf8(&output.stderr)?
            );
        } else {
            tracing::error!("else");
            let fid = FidItem {
                fid: String::from(""),
                data: "".into(),
            };
            rsync_list.push(Work {
                fid,
                src_file: src_file.into_os_string().into_string().unwrap(),
                dest_file,
            });

            if rsync_list.len() >= 500 {
                let mut rsync_res = do_rsync(&rsync_list).await?;

                result.append(&mut rsync_res);
                rsync_res.clear();
                rsync_list.clear();
            }
        }
    }
    let mut rsync_res = do_rsync(&rsync_list).await?;

    result.append(&mut rsync_res);
    Ok(result)
}

async fn restore_fids(
    llapi: LlapiFid,
    dest_src: &str,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let mut result = vec![];
    let mut rsync_list: Vec<Work> = vec![];
    let mpi_path = format!("{}/mpirun", env::get_openmpi_path());
    let mpi_count = env::get_openmpi_count();

    for fid in fid_list {
        let fid_path = match llapi.fid2path(&fid.fid) {
            Ok(x) => x,
            Err(_) => {
                tracing::error!("llapi: failed on fid {}", &fid.fid);
                continue;
            }
        };

        let dest_file = format!("{}/{}", llapi.mntpt(), &fid_path);
        let src_file = format!("{}/{}", &dest_src, &fid_path);

        let md = fs::metadata(&src_file).await?;
        /* invoking mpifileutils is slow, so only do it for directories
         * and big files, otherwise just use rsync
         */
        if md.is_dir() || (md.len() > LARGEFILE) {
            let output = Command::new(&mpi_path)
                .arg("--allow-run-as-root")
                .arg("-c")
                .arg(format!("{}", mpi_count))
                .arg("--hostfile")
                .arg("/etc/iml/filesync-hostfile")
                .arg("dsync")
                .arg("-S")
                .arg(src_file)
                .arg(dest_file)
                .output()
                .await?;

            if !output.status.success() {
                let FidItem { fid, data } = fid;
                result.push(FidError {
                    fid,
                    data,
                    errno: output.status.code().unwrap_or(1) as i16,
                });
            }
            tracing::debug!(
                "dsync exited with {} {} {}",
                output.status,
                std::str::from_utf8(&output.stdout)?,
                std::str::from_utf8(&output.stderr)?
            );
        } else {
            rsync_list.push(Work {
                fid,
                src_file,
                dest_file,
            });

            if rsync_list.len() >= 500 {
                let mut rsync_res = do_rsync(&rsync_list).await?;

                result.append(&mut rsync_res);
                rsync_res.clear();
                rsync_list.clear();
            }
        }
    }

    let mut rsync_res = do_rsync(&rsync_list).await?;

    result.append(&mut rsync_res);

    Ok(result)
}

arg_enum! {
    #[derive(Debug, serde::Deserialize, Clone, Copy, PartialEq)]
    #[serde(rename_all = "lowercase")]
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

pub async fn process_files(
    (fsname_or_mntpath, task_args, file_list): (PathBuf, TaskArgs, Vec<PathBuf>),
) -> Result<Vec<FidError>, ImlAgentError> {
    match task_args.action {
        ActionType::Push => archive_files(&task_args.remote, fsname_or_mntpath, file_list).await,
        ActionType::Pull => restore_files(&task_args.remote, fsname_or_mntpath, file_list).await,
    }
}
