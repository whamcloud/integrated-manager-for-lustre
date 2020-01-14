// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, lustre};
use futures::TryFutureExt;

/// Runs lctl with given arguments
pub async fn lctl(args: Vec<String>) -> Result<String, ImlAgentError> {
    lustre::lctl(args.iter().map(|s| s.as_ref()).collect())
        .await
        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
}

/// Executes `mountpoint -q /mnt/something`
/// It provides no output, but signals the caller with the exit code
pub async fn is_mounted(mount_point: String) -> Result<bool, ImlAgentError> {
    let args = vec!["-q", &mount_point];
    let output = iml_cmd::cmd_output("mountpoint", args).await?;
    Ok(output.status.success())
}

/// According to http://wiki.lustre.org/Mounting_a_Lustre_File_System_on_Client_Nodes
/// we need to execute mount command
/// ```bash
///   mount -t lustre \
///     [-o <options> ] \
///     <MGS NID>[:<MGS NID>]:/<fsname> \
///     /lustre/<fsname>
/// ```
/// An example for `lustre_device` is `192.168.0.100@tcp0:/spfs` and for `mount_point` is `/mnt/lustre`
pub async fn try_mount(
    (lustre_device, mount_point): (String, String),
) -> Result<(), ImlAgentError> {
    let args = vec!["-t", "lustre", &lustre_device, &mount_point];
    iml_cmd::cmd_output_success("mount", args).err_into().await.map(drop)
}
