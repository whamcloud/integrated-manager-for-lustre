use crate::agent_error::ImlAgentError;

use kmod;

pub async fn loaded(module: String) -> Result<bool, ImlAgentError> {
    let ctx = kmod::Context::new()?;

    let mut result = false;
    for m in ctx.modules_loaded()? {
        let name = m.name();

        if name == module {
            result = true;
        } else {
            continue;
        }
    }
    Ok(result)
}
