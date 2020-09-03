// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::TryFutureExt;
use iml_cmd::{CheckedCommandExt, Command};
use liblustreapi::LlapiFid;
use std::ffi::OsStr;
use tokio::task::spawn_blocking;

/// Runs lctl with given arguments
pub async fn lctl<I, S>(args: I) -> Result<String, ImlAgentError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    Command::new("/usr/sbin/lctl")
        .args(args)
        .checked_output()
        .err_into()
        .await
        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
}

/// Returns LlapiFid for a given device or mount path
pub async fn search_rootpath(device: String) -> Result<LlapiFid, ImlAgentError> {
    spawn_blocking(move || LlapiFid::create(&device).map_err(ImlAgentError::from))
        .err_into()
        .await
        .and_then(std::convert::identity)
}
