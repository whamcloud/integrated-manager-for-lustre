use crate::agent_error::{ImlAgentError, MyKmodError};

use kmod;

pub async fn loaded(module: String) -> Result<bool, ImlAgentError> {
    let ctx = kmod::Context::new().map_err(|e| MyKmodError::from(e))?;

    let mut result = false;
    for m in ctx.modules_loaded().map_err(|e| MyKmodError::from(e))? {
        let name = m.name();

        if name == module {
            result = true;
        } else {
            continue;
        }
    }
    Ok(result)
}
