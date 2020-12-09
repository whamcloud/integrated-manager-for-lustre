// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use iml_cmd::{CheckedCommandExt, Command};

pub async fn loaded(module: String) -> Result<bool, ImlAgentError> {
    let output = Command::new("lsmod")
        .kill_on_drop(true)
        .checked_output()
        .await?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let module = stdout.lines().find(|m| {
        let mut fields = m.split(' ').filter(|s| *s != "");
        let name = fields.next();
        name == Some(&module)
    });

    Ok(module.is_some())
}

pub async fn version(module: String) -> Result<String, ImlAgentError> {
    let output = Command::new("modinfo")
        .args(&["-F", "version", &module])
        .kill_on_drop(true)
        .checked_output()
        .await?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let version = stdout.trim().to_string();

    Ok(version)
}
