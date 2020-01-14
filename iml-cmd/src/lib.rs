// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryFutureExt;
use std::{error, ffi::OsStr, fmt, io, process::Output};
use tokio::process::Command;

#[derive(Debug)]
pub enum CmdError {
    Io(io::Error),
    Output(Output),
}

impl fmt::Display for CmdError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            CmdError::Io(ref err) => write!(f, "{}", err),
            CmdError::Output(ref err) => write!(
                f,
                "{}, stdout: {}, stderr: {}",
                err.status,
                String::from_utf8_lossy(&err.stdout),
                String::from_utf8_lossy(&err.stderr)
            ),
        }
    }
}

impl std::error::Error for CmdError {
    fn source(&self) -> Option<&(dyn error::Error + 'static)> {
        match *self {
            CmdError::Io(ref err) => Some(err),
            CmdError::Output(_) => None,
        }
    }
}

impl From<io::Error> for CmdError {
    fn from(err: io::Error) -> Self {
        CmdError::Io(err)
    }
}

impl From<Output> for CmdError {
    fn from(output: Output) -> Self {
        CmdError::Output(output)
    }
}

/// Runs an arbitrary command and collects all output
///
/// # Arguments
///
/// * `program` - The program to run
/// * `xs` - The args to pass to the systemctl call. `xs` Implements `IntoIterator`
pub async fn cmd_output<S, I>(program: S, xs: I) -> Result<Output, CmdError>
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
pub async fn cmd_output_success<S, I>(program: S, xs: I) -> Result<Output, CmdError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let x = cmd_output(program, xs).await?;

    if x.status.success() {
        Ok(x)
    } else {
        Err(x.into())
    }
}

/// Runs lctl with given arguments
pub async fn lctl(args: Vec<&str>) -> Result<Output, CmdError> {
    cmd_output_success("/usr/sbin/lctl", args).await
}
