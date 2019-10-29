// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures01::Future;
use std::{ffi::OsStr, process::Command};
use tokio_process::CommandExt;

/// Runs an arbitrary command and collects all output
///
/// # Arguments
///
/// * `program` - The program to run
/// * `xs` - The args to pass to the systemctl call. `xs` Implements `IntoIterator`
pub fn cmd_output<S>(
    program: S,
    xs: &[&str],
) -> impl Future<Item = std::process::Output, Error = ImlAgentError>
where
    S: AsRef<OsStr>,
{
    Command::new(program).args(xs).output_async().from_err()
}

/// Runs an arbitrary command and collects all output
///
/// Returns `Error` if the command did not succeed.
///
/// # Arguments
///
/// * `program` - The program to run
/// * `xs` - The args to pass to the systemctl call. `xs` Implements `IntoIterator`
pub fn cmd_output_success<S>(
    program: S,
    xs: &[&str],
) -> impl Future<Item = std::process::Output, Error = ImlAgentError>
where
    S: AsRef<OsStr>,
{
    cmd_output(program, xs).and_then(|x| {
        if x.status.success() {
            Ok(x)
        } else {
            Err(ImlAgentError::CmdOutputError(x))
        }
    })
}
