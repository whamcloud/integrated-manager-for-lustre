// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output};
use futures01::{
    future::{self, loop_fn, Either, Loop},
    Future,
};
use std::time::{Duration, Instant};
use tokio::timer::Delay;

pub fn checked_cmd(
    action: &str,
    service: &'static str,
) -> impl Future<Item = bool, Error = ImlAgentError> {
    cmd_output("systemctl", &[action, service]).and_then(move |_| {
        loop_fn(1, move |cnt| {
            systemctl_status(service)
                .map(did_succeed)
                .and_then(move |started| {
                    if started {
                        Either::A(future::ok(Loop::Break(true)))
                    } else if cnt == 5 {
                        Either::A(future::ok(Loop::Break(false)))
                    } else {
                        Either::B(
                            Delay::new(Instant::now() + Duration::from_millis(250))
                                .from_err()
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
pub fn systemctl_start(x: &'static str) -> impl Future<Item = bool, Error = ImlAgentError> {
    checked_cmd("start", x)
}

/// Stops a service
///
/// # Arguments
///
/// * `x` - The service to stop
pub fn systemctl_stop(x: &'static str) -> impl Future<Item = bool, Error = ImlAgentError> {
    checked_cmd("stop", x)
}

/// Checks if a service is active
///
/// # Arguments
///
/// * `x` - The service to check
pub fn systemctl_status(
    x: &str,
) -> impl Future<Item = std::process::Output, Error = ImlAgentError> {
    cmd_output("systemctl", &["is-active", x, "--quiet"])
}

/// Invokes `success` on `ExitStatus` within `Output`
///
/// # Arguments
///
/// * `x` - The `Output` to check
pub fn did_succeed(x: std::process::Output) -> bool {
    x.status.success()
}
