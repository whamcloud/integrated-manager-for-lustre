// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use emf_cmd::{CheckedCommandExt, CmdError, Command};

static NOT_RUNNING: i32 = 252;
static DUPLICATE_MESSAGE: &[u8] = b"Warning: ALREADY_ENABLED\n";

async fn port_change(action: &str, port: u16, proto: String) -> Result<(), EmfAgentError> {
    Command::new("firewall-cmd")
        .arg(format!("--{}-port={}/{}", action, port, proto))
        .kill_on_drop(true)
        .checked_output()
        .await
        .map(drop)
        .or_else(|e| match e {
            CmdError::Output(o) if o.status.code() == Some(NOT_RUNNING) => Ok(()),
            CmdError::Output(o) if o.stdout == DUPLICATE_MESSAGE => Ok(()),
            x => Err(x),
        })
        .map_err(EmfAgentError::from)
}

pub(crate) async fn add_port((port, proto): (u16, String)) -> Result<(), EmfAgentError> {
    port_change("add", port, proto).await
}

pub(crate) async fn remove_port((port, proto): (u16, String)) -> Result<(), EmfAgentError> {
    port_change("remove", port, proto).await
}
