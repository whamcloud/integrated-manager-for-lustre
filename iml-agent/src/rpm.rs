use regex::Regex;

use std::process::Output;

use crate::{agent_error::ImlAgentError, cmd::cmd_output};

fn parse(output: Output) -> Result<bool, ImlAgentError> {
    if output.status.success() {
        Ok(true)
    } else {
        let stdout = output.stdout.clone();
        let re = Regex::new(r"^package .*? is not installed\n$").unwrap();
        let s = String::from_utf8(stdout)?;
        if re.is_match(&s) {
            Ok(false)
        } else {
            Err(ImlAgentError::CmdOutputError(output))
        }
    }
}

pub(crate) async fn installed(package_name: &str) -> Result<bool, ImlAgentError> {
    let output = cmd_output("rpm", vec!["--query", package_name]).await?;
    parse(output)
}
