use crate::{agent_error::ImlAgentError, rpm};

pub use rpm::Version;

pub async fn installed(package: String) -> Result<bool, ImlAgentError> {
    rpm::installed(&package).await
}

pub async fn version(package: String) -> Result<Option<Version>, ImlAgentError> {
    rpm::version(&package).await
}
