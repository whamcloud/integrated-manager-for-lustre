// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, lustre::lctl};
use iml_wire_types::snapshot::{Create, Destroy, Mount, Unmount};

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