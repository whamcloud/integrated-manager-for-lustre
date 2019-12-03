use regex::Regex;

use std::process::Output;

use crate::{agent_error::ImlAgentError, cmd::cmd_output};

enum PackageState {
    Installed(Version),
    NotInstalled,
}

struct Version(String);

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum RpmResult {
    Ok(String),
    Err(RpmError),
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum RpmError {
    PackageNotInstalled,
}

async fn parse(output: Output) -> Result<PackageState, ImlAgentError> {
    if output.status.success() {
        // In case there's syntax error in query format, exit code of `rpm` is 0,
        // but there's no data and an error is on stderr
        if output.stderr.len() > 0 {
            Err(ImlAgentError::CmdOutputError(output))
        } else {
            Ok(PackageState::Installed(Version(
                String::from_utf8(output.stdout).unwrap(),
            )))
        }
    } else {
        let stdout = output.stdout.clone();
        let re = Regex::new(r"^package .*? is not installed\n$").unwrap();
        let s = String::from_utf8(stdout)?;
        if re.is_match(&s) {
            Ok(PackageState::NotInstalled)
        } else {
            Err(ImlAgentError::CmdOutputError(output))
        }
    }
}

async fn run_rpm(package_name: &str) -> Result<Output, ImlAgentError> {
    cmd_output(
        "rpm",
        vec!["--query", "--queryformat", "${VERSION}", package_name],
    )
    .await
}

pub(crate) async fn installed(package_name: &str) -> Result<bool, ImlAgentError> {
    let output = run_rpm(package_name).await?;
    parse(output).await.map(|r| match r {
        PackageState::Installed(_) => true,
        PackageState::NotInstalled => false,
    })
}

pub(crate) async fn version(package_name: &str) -> Result<RpmResult, ImlAgentError> {
    let output = run_rpm(package_name).await?;
    match parse(output).await {
        Ok(PackageState::Installed(Version(s))) => Ok(RpmResult::Ok(s)),
        Ok(PackageState::NotInstalled) => Ok(RpmResult::Err(RpmError::PackageNotInstalled)),
        Err(e) => Err(e),
    }
}
