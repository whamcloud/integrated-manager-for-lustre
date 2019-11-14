use crate::{agent_error::ImlAgentError, cmd::cmd_output};

pub async fn check_stratagem(_: ()) -> Result<bool, ImlAgentError> {
    let rpm = cmd_output("rpm", vec!["--query", "lipe"]).await?;
    if rpm.status.success() {
        Ok(true)
    } else {
        Ok(false)
    }
}
