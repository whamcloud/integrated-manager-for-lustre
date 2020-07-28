// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::TryFutureExt;
use iml_cmd::{CheckedCommandExt, Command};

/// According to http://wiki.lustre.org/Mounting_a_Lustre_File_System_on_Client_Nodes
/// we need to execute mount command
/// ```bash
///   mount -t lustre \
///     [-o <options> ] \
///     <MGS NID>[:<MGS NID>]:/<fsname> \
///     /lustre/<fsname>
/// ```
/// An example for `lustre_device` is `192.168.0.100@tcp0:/spfs` and for `mount_point` is `/mnt/lustre`
pub async fn mount((lustre_device, mount_point): (String, String)) -> Result<(), ImlAgentError> {
    let args = vec!["-t", "lustre", &lustre_device, &mount_point];
    Command::new("mount")
        .args(args)
        .checked_output()
        .err_into()
        .await
        .map(drop)
}
