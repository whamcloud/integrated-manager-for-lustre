// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::{
    future::{self, loop_fn, Either, Loop},
    Future,
};
use std::{
    ffi::OsStr,
    process::Command,
    time::{Duration, Instant},
};
use tokio::timer::Delay;
use tokio_process::CommandExt;

/// Runs an arbitrary systemctl command
///
/// # Arguments
///
/// * `xs` - The args to pass to the systemctl call. `xs` Implements `IntoIterator`
pub fn systemctl_cmd<S>(
    xs: Vec<S>,
) -> impl Future<Item = std::process::Output, Error = ImlAgentError>
where
    S: AsRef<OsStr>,
{
    let child = Command::new("systemctl").args(xs).output_async();

    child.map_err(|e| e.into())
}

pub fn checked_cmd(
    action: String,
    service: String,
) -> impl Future<Item = bool, Error = ImlAgentError> {
    systemctl_cmd(vec![action.clone(), service.clone()]).and_then(|_| {
        loop_fn(1, move |cnt| {
            systemctl_status(service.clone())
                .map(did_succeed)
                .and_then(move |started| {
                    if started {
                        Either::A(future::ok(Loop::Break(true)))
                    } else if cnt == 5 {
                        Either::A(future::ok(Loop::Break(false)))
                    } else {
                        Either::B(
                            Delay::new(Instant::now() + Duration::from_millis(250))
                                .map_err(|e| e.into())
                                .map(move |_| Loop::Continue(cnt + 1)),
                        )
                    }
                })
        })
    })
}

/// Starts a service
///
/// # Arguments
///
/// * `x` - The service to start
pub fn systemctl_start(x: String) -> impl Future<Item = bool, Error = ImlAgentError> {
    checked_cmd("start".to_string(), x)
}

/// Stops a service
///
/// # Arguments
///
/// * `x` - The service to stop
pub fn systemctl_stop(x: String) -> impl Future<Item = bool, Error = ImlAgentError> {
    checked_cmd("stop".to_string(), x)
}

/// Checks if a service is active
///
/// # Arguments
///
/// * `x` - The service to check
pub fn systemctl_status(
    x: String,
) -> impl Future<Item = std::process::Output, Error = ImlAgentError> {
    systemctl_cmd(vec!["is-active".to_string(), x, "--quiet".to_string()])
}

/// Invokes `success` on `ExitStatus` within `Output`
///
/// # Arguments
///
/// * `x` - The `Output` to check
pub fn did_succeed(x: std::process::Output) -> bool {
    x.status.success()
}
