// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output};
use std::time::{Duration, Instant};
use tokio::timer::delay;

pub async fn checked_cmd(action: &str, service: &'static str) -> Result<bool, ImlAgentError> {
    cmd_output("systemctl", vec![action, service]).await?;

    for _ in 0_u32..5 {
        let x = systemctl_status(service).await?;

        if did_succeed(x) {
            return Ok(true);
        }

        delay(Instant::now() + Duration::from_millis(250)).await;
    }

    Ok(false)
}

/// Starts a service
///
/// # Arguments
///
/// * `x` - The service to start
pub async fn systemctl_start(x: &'static str) -> Result<bool, ImlAgentError> {
    checked_cmd("start", x).await
}

/// Restarts a service
///
/// # Arguments
///
/// * `x` - The service to start
pub async fn systemctl_restart(x: &'static str) -> Result<bool, ImlAgentError> {
    checked_cmd("restart", x).await
}

/// Stops a service
///
/// # Arguments
///
/// * `x` - The service to stop
pub async fn systemctl_stop(x: &'static str) -> Result<bool, ImlAgentError> {
    checked_cmd("stop", x).await
}

/// Checks if a service is active
///
/// # Arguments
///
/// * `x` - The service to check
pub async fn systemctl_status(x: &str) -> Result<std::process::Output, ImlAgentError> {
    cmd_output("systemctl", vec!["is-active", x, "--quiet"]).await
}

/// Checks if a service is enabled
///
/// # Arguments
///
/// * `x` - The service to check
pub async fn systemctl_enabled(x: &str) -> Result<std::process::Output, ImlAgentError> {
    cmd_output("systemctl", vec!["is-enabled", x, "--quiet"]).await
}

/// Invokes `success` on `ExitStatus` within `Output`
///
/// # Arguments
///
/// * `x` - The `Output` to check
pub fn did_succeed(x: std::process::Output) -> bool {
    x.status.success()
}
