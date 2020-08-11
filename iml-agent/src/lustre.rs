use crate::agent_error::ImlAgentError;
use futures::TryFutureExt;
use iml_cmd::{CheckedCommandExt, Command};
use std::ffi::OsStr;

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
