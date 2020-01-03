// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success};

pub async fn loaded(module: String) -> Result<bool, ImlAgentError> {
    let output = cmd_output_success("lsmod", vec![]).await?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let module = stdout.lines().into_iter().find(|m| {
        let mut fields = m.split(' ').filter(|s| *s != "");
        let name = fields.next();
        name == Some(&module)
    });

    Ok(module.is_some())
}

pub async fn version(module: String) -> Result<String, ImlAgentError> {
    let output = cmd_output_success("modinfo", vec!["-F", "version", &module]).await?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let version = stdout.trim().to_string();

    Ok(version)
}
