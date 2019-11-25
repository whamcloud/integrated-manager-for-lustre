use crate::{agent_error::ImlAgentError, rpm};

pub async fn package_installed(package: String) -> Result<bool, ImlAgentError> {
    rpm::installed(&package).await
}
