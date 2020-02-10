use crate::agent_error::ImlAgentError;
use futures::TryFutureExt;
use iml_cmd::{CheckedCommandExt, Command};

pub async fn lctl(args: Vec<&str>) -> Result<std::process::Output, ImlAgentError> {
    Command::new("/usr/sbin/lctl")
        .args(args)
        .checked_output()
        .err_into()
        .await
}
