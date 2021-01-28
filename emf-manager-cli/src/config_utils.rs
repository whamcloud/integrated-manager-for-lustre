// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::EmfManagerCliError;
use emf_cmd::CheckedCommandExt;

pub async fn su(user: &str, cmd: &str) -> Result<String, EmfManagerCliError> {
    let out = emf_cmd::Command::new("su")
        .arg("-l")
        .arg(user)
        .arg("-c")
        .arg(cmd)
        .checked_output()
        .await?;
    Ok(String::from_utf8_lossy(&out.stdout).to_string())
}

pub async fn psql(cmd: &str) -> Result<String, EmfManagerCliError> {
    su("postgres", format!(r#"psql -tAc "{}""#, cmd).as_str()).await
}
