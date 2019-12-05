use regex::Regex;

use std::fmt;
use std::process::Output;
use std::result::Result as StdResult;

use crate::{agent_error::ImlAgentError, cmd::cmd_output};

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Version(String);

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

async fn parse(output: Output) -> StdResult<Option<Version>, ImlAgentError> {
    if output.status.success() {
        // In case there's syntax error in query format, exit code of `rpm` is 0,
        // but there's no data and an error is on stderr
        if output.stderr.len() > 0 {
            Err(ImlAgentError::CmdOutputError(output))
        } else {
            Ok(Some(Version(
                String::from_utf8_lossy(&output.stdout).to_string(),
            )))
        }
    } else {
        let stdout = output.stdout.clone();
        let re = Regex::new(r"^package .*? is not installed\n$").unwrap();
        let s = String::from_utf8(stdout)?;
        if re.is_match(&s) {
            Ok(None)
        } else {
            Err(ImlAgentError::CmdOutputError(output))
        }
    }
}

pub(crate) async fn installed(package_name: &str) -> StdResult<bool, ImlAgentError> {
    version(package_name).await.map(|r| r.is_some())
}

pub(crate) async fn version(package_name: &str) -> StdResult<Option<Version>, ImlAgentError> {
    let output = cmd_output(
        "rpm",
        vec!["--query", "--queryformat", "%{VERSION}", package_name],
    )
    .await?;
    parse(output).await
}
