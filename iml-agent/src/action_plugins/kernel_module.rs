// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output};

pub async fn loaded(module: String) -> Result<bool, ImlAgentError> {
    let output = cmd_output("lsmod", vec![]).await?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut modules = stdout.lines().into_iter().filter_map(|m| {
            let mut fields = m.split(' ').filter(|s| *s != "");
            let (name, _, refcount) = (fields.next(), fields.next(), fields.next());
            let refcount = refcount.map(|x| x.parse::<u32>());
            if let (Some(name), Some(Ok(refcount))) = (name, refcount) {
                Some((name, refcount))
            } else {
                None
            }
        });

        let module = modules.find(|(m, refcount)| *m == module && *refcount > 0);

        if module.is_some() {
            Ok(true)
        } else {
            Ok(false)
        }
    } else {
        Err(ImlAgentError::CmdOutputError(output))
    }
}
