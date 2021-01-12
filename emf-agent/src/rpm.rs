// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use emf_cmd::Command;
use regex::Regex;
use std::{fmt, process::Output, str};

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct Version(String);

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

fn parse(output: Output) -> Result<Option<Version>, EmfAgentError> {
    if output.status.success() {
        // In case there's syntax error in query format, exit code of `rpm` is 0,
        // but there's no data and an error is on stderr
        if !output.stderr.is_empty() {
            Err(output.into())
        } else {
            Ok(Some(Version(
                String::from_utf8_lossy(&output.stdout).to_string(),
            )))
        }
    } else {
        let re = Regex::new(r"^package .*? is not installed\n$").unwrap();
        let s = str::from_utf8(&output.stdout)?;
        if re.is_match(&s) {
            Ok(None)
        } else {
            Err(output.into())
        }
    }
}

pub(crate) async fn installed(package_name: &str) -> Result<bool, EmfAgentError> {
    version(package_name).await.map(|r| r.is_some())
}

pub(crate) async fn version(package_name: &str) -> Result<Option<Version>, EmfAgentError> {
    let output = Command::new("rpm")
        .args(&["--query", "--queryformat", "%{VERSION}", package_name])
        .kill_on_drop(true)
        .output()
        .await?;
    parse(output)
}
