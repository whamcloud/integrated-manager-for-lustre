// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use iml_cmd::{CheckedCommandExt, Command};
use version_utils::Version;

async fn check_kver_module(module: &str, kver: &str) -> Result<bool, ImlAgentError> {
    Command::new("modinfo")
        .args(&["-n", "-k", kver, module])
        .kill_on_drop(true)
        .checked_status()
        .await?;

    Ok(true)
}

pub async fn get_kernel(modules: Vec<String>) -> Result<String, ImlAgentError> {
    let output = Command::new("rpm")
        .args(&["-q", "--qf", "%{V}-%{R}.%{ARCH}\n", "kernel"])
        .kill_on_drop(true)
        .checked_output()
        .await?;

    let mut newest = Version::from("");

    for kver in std::str::from_utf8(output.stdout.as_slice())?.lines() {
        let contender = Version::from(kver);
        if contender <= newest {
            continue;
        }
        let mut okay = true;
        for module in modules.iter() {
            if !check_kver_module(&module, kver).await? {
                okay = false;
                break;
            }
        }
        if okay {
            newest = contender;
        }
    }
    Ok(newest.version)
}
