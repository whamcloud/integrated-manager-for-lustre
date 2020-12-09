// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use iml_cmd::{CheckedCommandExt, Command};

/// For more information on LNet operations see: https://wiki.lustre.org/Starting_and_Stopping_LNet

/// Loads LNet
pub async fn load(_args: Vec<String>) -> Result<(), ImlAgentError> {
    Command::new("modprobe")
        .arg("lnet")
        .checked_status()
        .await?;

    Ok(())
}

/// Unloads LNet
pub async fn unload(_args: Vec<String>) -> Result<(), ImlAgentError> {
    Command::new("lustre_rmmod").checked_status().await?;

    Ok(())
}

/// Starts LNet
pub async fn start(_args: Vec<String>) -> Result<(), ImlAgentError> {
    Command::new("lnetctl")
        .args(&["lnet", "configure", "--all"])
        .checked_status()
        .await?;

    Ok(())
}

/// Stops LNet
pub async fn stop(_args: Vec<String>) -> Result<(), ImlAgentError> {
    Command::new("lustre_rmmod")
        .arg("ptlrpc")
        .checked_status()
        .await?;

    Command::new("lnetctl")
        .args(&["lnet", "unconfigure"])
        .checked_status()
        .await?;

    Ok(())
}
