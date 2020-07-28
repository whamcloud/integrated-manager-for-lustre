// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use iml_cmd::{CheckedCommandExt, Command};

pub async fn mount(filesystem_name: String, snapshot_name: String) -> Result<(), ImlAgentError> {
    Command::new("lctl")
        .arg("snapshot_mount")
        .arg("--fsname")
        .arg(filesystem_name)
        .arg("--name")
        .arg(snapshot_name)
        .checked_status()
        .await
        .map_err(|e| e.into())
}

pub async fn unmount(snapshot_name: String) -> Result<(), ImlAgentError> {
    Command::new("lctl")
        .arg("snapshot_unmount")
        .arg("--name")
        .arg(snapshot_name)
        .checked_status()
        .await
        .map_err(|e| e.into())
}
