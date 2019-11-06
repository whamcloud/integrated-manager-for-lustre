// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::TryFutureExt;
use std::ffi::OsStr;
use tokio_net::process::Command;

/// Runs an arbitrary command and collects all output
///
/// # Arguments
///
/// * `program` - The program to run
/// * `xs` - The args to pass to the systemctl call. `xs` Implements `IntoIterator`
pub async fn cmd_output<S, I>(program: S, xs: I) -> Result<std::process::Output, ImlAgentError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    Command::new(program).args(xs).output().err_into().await
}

/// Runs an arbitrary command and collects all output
/// Returns `Error` if the command did not succeed.
///
/// # Arguments
///
/// * `program` - The program to run
/// * `xs` - The args to pass to the systemctl call. `xs` Implements `IntoIterator`
pub async fn cmd_output_success<S, I>(
    program: S,
    xs: I,
) -> Result<std::process::Output, ImlAgentError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let x = cmd_output(program, xs).await?;

    if x.status.success() {
        Ok(x)
    } else {
        Err(ImlAgentError::CmdOutputError(x))
    }
}
