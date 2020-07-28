// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, lustre::lctl};
use structopt::StructOpt;

#[derive(serde::Deserialize, Debug, StructOpt)]
pub struct Create {
    /// Filesystem name
    fsname: String,
    /// Snapshot name
    name: String,

    /// Optional comment for the snapshot
    #[structopt(short = "c", long = "comment")]
    comment: Option<String>,
}

pub async fn create(c: Create) -> Result<(), ImlAgentError> {
    let mut args = vec!["snapshot_create", "--fsname", &c.fsname, "--name", &c.name];
    if let Some(cmnt) = &c.comment {
        args.push("--comment");
        args.push(cmnt);
    }
    lctl(args).await.map(drop)
}

#[derive(serde::Deserialize, Debug, StructOpt)]
pub struct Destroy {
    /// Filesystem name
    fsname: String,
    /// Name of the snapshot to destroy
    name: String,

    /// Destroy the snapshot by force
    #[structopt(short = "f", long = "--force")]
    force: bool,
}

pub async fn destroy(d: Destroy) -> Result<(), ImlAgentError> {
    let mut args = vec!["snapshot_destroy", "--fsname", &d.fsname, "--name", &d.name];
    if d.force {
        args.push("--force");
    }
    lctl(args).await.map(drop)
}

pub async fn mount(filesystem_name: String, snapshot_name: String) -> Result<(), ImlAgentError> {
    let args = &[
        "snapshot_mount",
        "--fsname",
        &filesystem_name,
        "--name",
        &snapshot_name,
    ];
    lctl(args).await.map(drop)
}

pub async fn unmount(snapshot_name: String) -> Result<(), ImlAgentError> {
    let args = &["snapshot_unmount", "--name", &snapshot_name];
    lctl(args).await.map(drop)
}
