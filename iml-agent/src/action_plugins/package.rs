use crate::{agent_error::ImlAgentError, rpm};

pub use rpm::RpmResult;

pub async fn installed(package: String) -> Result<bool, ImlAgentError> {
    rpm::installed(&package).await
}

pub async fn version(package: String) -> Result<RpmResult, ImlAgentError> {
    rpm::version(&package).await
}
