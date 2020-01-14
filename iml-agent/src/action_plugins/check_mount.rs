// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output, cmd::cmd_output_success};
use tokio::process::{Child, Command};
use std::process::Output;

pub async fn is_filesystem_mounted(mount_point: &str) -> std::io::Result<bool> {
    // `mountpoint -q /mnt/something` produces no output,
    // but signals the caller with the exit code
    let process: Child = Command::new("mountpoint")
        .arg("-q")
        .arg(mount_point)
        .spawn()?;
    let output: Output = process.wait_with_output().await?;
    Ok(output.status.success())
}
