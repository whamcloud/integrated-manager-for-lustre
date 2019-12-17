// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use kmod;
use tokio_executor::blocking::run;

pub async fn loaded(module: String) -> Result<bool, ImlAgentError> {
    run(move || {
        let ctx = kmod::Context::new()?;

        Ok(ctx.modules_loaded()?.find(|m| m.name() == module).is_some())
    })
    .await
}
