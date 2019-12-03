use regex::Regex;

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

async fn parse(package_name: &str) -> Result<PackageState, ImlAgentError> {
    // XXX: In case there's syntax error in query format, exit code of `rpm` is 0, but there's no data
    let output = cmd_output("rpm", vec!["--query", "--queryformat", "%{VERSION}", package_name]).await?;
    if output.status.success() {
        Ok(PackageState::Installed(Version(String::from_utf8(output.stdout).unwrap())))
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

pub(crate) async fn installed(package_name: &str) -> Result<bool, ImlAgentError> {
    parse(package_name).await.map(|r| match r {
        PackageState::Installed(_) => true,
        PackageState::NotInstalled => false,
    })
}

pub(crate) async fn version(package_name: &str) -> Result<RpmResult, ImlAgentError> {
    match parse(package_name).await {
        Ok(PackageState::Installed(Version(s))) => Ok(RpmResult::Ok(s)),
        Ok(PackageState::NotInstalled) => Ok(RpmResult::Err(RpmError::PackageNotInstalled)),
        Err(e) => Err(e),
    }
}
