// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, lustre::lctl};
use combine::{stream::easy, EasyParser};
use iml_wire_types::snapshot::{Create, Destroy, List, Mount, Snapshot, Unmount};

mod parse;

pub async fn list(l: List) -> Result<Vec<Snapshot>, ImlAgentError> {
    let mut args = vec!["snapshot_list", "--fsname", &l.fsname];
    if let Some(name) = &l.name {
        args.push("--name");
        args.push(name);
    }
    if l.detail {
        args.push("--detail");
    }
    let stdout = lctl(args).await?;
    parse_snapshot_list(&stdout).map_err(ImlAgentError::CombineEasyError)
}

fn parse_snapshot_list(input: &str) -> Result<Vec<Snapshot>, easy::Errors<char, String, usize>> {
    let (snapshots, _) = parse::parse().easy_parse(input).map_err(|err| {
        err.map_position(|p| p.translate_position(input))
            .map_range(String::from)
    })?;
    Ok(snapshots)
}

pub async fn create(c: Create) -> Result<(), ImlAgentError> {
    let mut args = vec!["snapshot_create", "--fsname", &c.fsname, "--name", &c.name];
    if let Some(cmnt) = &c.comment {
        args.push("--comment");
        args.push(cmnt);
    }
    lctl(args).await.map(drop)
}

pub async fn destroy(d: Destroy) -> Result<(), ImlAgentError> {
    let mut args = vec!["snapshot_destroy", "--fsname", &d.fsname, "--name", &d.name];
    if d.force {
        args.push("--force");
    }
    lctl(args).await.map(drop)
}

pub async fn mount(m: Mount) -> Result<(), ImlAgentError> {
    let args = &["snapshot_mount", "--fsname", &m.fsname, "--name", &m.name];
    lctl(args).await.map(drop)
}

pub async fn unmount(u: Unmount) -> Result<(), ImlAgentError> {
    let args = &["snapshot_umount", "--fsname", &u.fsname, "--name", &u.name];
    lctl(args).await.map(drop)
}
