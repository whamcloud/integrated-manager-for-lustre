use crate::{agent_error::ImlAgentError, rpm};

pub async fn check_stratagem(_: ()) -> Result<bool, ImlAgentError> {
    rpm::query("lipe").await
}
