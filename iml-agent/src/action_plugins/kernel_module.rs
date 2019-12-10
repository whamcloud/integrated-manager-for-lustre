// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::{ImlAgentError, KernelModuleError};
use kmod;
use tokio_executor::blocking::run;

pub async fn is_loaded(module: String) -> Result<bool, ImlAgentError> {
    run(move || {
        let ctx = kmod::Context::new()?;

        Ok(ctx.modules_loaded()?.find(|m| m.name() == module).is_some())
    })
    .await
}

pub async fn version(module: String) -> Result<String, ImlAgentError> {
    run(move || {
        let ctx = kmod::Context::new()?;

        let m = ctx.modules_loaded()?.find(|m| m.name() == module);

        if let Some(m) = m {
            let i = m.info()?.to_map();
            let vv = &i.get("version");
            if vv.is_none() {
                return Err(ImlAgentError::KernelModuleError(
                    KernelModuleError::HasNoVersion,
                ));
            }
            let vv = vv.unwrap();
            if vv.len() > 1 {
                return Err(ImlAgentError::KernelModuleError(
                    KernelModuleError::HasMultipleVersions,
                ));
            }
            let v = &vv[0];

            Ok(v.clone())
        } else {
            Err(ImlAgentError::KernelModuleError(
                KernelModuleError::NotLoaded,
            ))
        }
    })
    .await
}
