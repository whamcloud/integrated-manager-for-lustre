use crate::{agent_error::ImlAgentError, rpm};

pub async fn package_version(package: String) -> Result<bool, ImlAgentError> {
    rpm::version(&package).await
}
