use crate::agent_error::ImlAgentError;
use futures::TryFutureExt;
use iml_cmd::cmd_output_success;

pub async fn lctl(args: Vec<&str>) -> Result<std::process::Output, ImlAgentError> {
    cmd_output_success("/usr/sbin/lctl", args).err_into().await
}
