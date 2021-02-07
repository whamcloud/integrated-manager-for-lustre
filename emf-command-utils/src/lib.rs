// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_tracing::tracing;
use emf_wire_types::Command;
use futures::channel::mpsc;
use std::{collections::HashSet, iter, time::Duration};
use tokio::time::delay_for;

#[derive(Debug, thiserror::Error)]
pub enum CmdUtilError {
    #[error(transparent)]
    EmfManagerClientError(#[from] emf_manager_client::EmfManagerClientError),
    #[error("Failed commands: {0:?}")]
    FailedCommandError(Vec<Command>),
}

impl From<Vec<Command>> for CmdUtilError {
    fn from(xs: Vec<Command>) -> Self {
        CmdUtilError::FailedCommandError(xs)
    }
}

pub enum Progress {
    Update(i32),
    Complete(Command),
}

pub async fn wait_for_cmds_progress(
    cmds: &[Command],
    tx: Option<mpsc::UnboundedSender<Progress>>,
) -> Result<Vec<Command>, CmdUtilError> {
    unimplemented!();
}

/// Waits for command completion and prints progress messages.
/// This will error on command failure and print failed commands in the error message.
pub async fn wait_for_cmds_success(
    cmds: &[Command],
    tx: Option<mpsc::UnboundedSender<Progress>>,
) -> Result<Vec<Command>, CmdUtilError> {
    unimplemented!();
}

fn cmd_finished(cmd: &Command) -> bool {
    unimplemented!();
}
