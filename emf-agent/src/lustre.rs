// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use emf_cmd::{CheckedCommandExt, Command};
use futures::TryFutureExt;
use liblustreapi::LlapiFid;
use std::ffi::OsStr;
use tokio::task::spawn_blocking;

/// Runs lctl with given arguments
pub async fn lctl<I, S>(args: I) -> Result<String, EmfAgentError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    Command::new("/usr/sbin/lctl")
        .args(args)
        .kill_on_drop(true)
        .checked_output()
        .err_into()
        .await
        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
}

/// Returns LlapiFid for a given device or mount path
pub async fn search_rootpath(device: String) -> Result<LlapiFid, EmfAgentError> {
    spawn_blocking(move || LlapiFid::create(&device).map_err(EmfAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity)
}

/// Find any MDT0s that exist on this node
pub async fn list_mdt0s() -> Vec<String> {
    lctl(vec!["get_param", "-N", "mdt.*-MDT0000"])
        .await
        .map(|o| {
            o.lines()
                .filter_map(|line| line.split('.').nth(1))
                .map(|s| s.to_string())
                .collect()
        })
        .unwrap_or_else(|_| vec![])
}
