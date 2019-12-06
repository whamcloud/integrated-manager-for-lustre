use crate::agent_error::ImlAgentError;

use kmod;

pub async fn loaded(module: String) -> Result<bool, ImlAgentError> {
    let ctx = kmod::Context::new()?;

    Ok(ctx.modules_loaded()?.find(|m| m.name() == module).is_some())
}
