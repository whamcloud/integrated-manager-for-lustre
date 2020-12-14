// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::channel::mpsc;
use iml_manager_client::header::HeaderMap;
use iml_tracing::tracing;
use iml_wire_types::{ApiList, Command, EndpointName as _};
use std::{collections::HashSet, iter, time::Duration};
use tokio::time::delay_for;

#[derive(Debug, thiserror::Error)]
pub enum CmdUtilError {
    #[error(transparent)]
    ImlManagerClientError(#[from] iml_manager_client::ImlManagerClientError),
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
    let mut state: HashSet<_> = cmds.iter().map(|x| x.id).collect();
    let mut settled_commands = vec![];

    loop {
        if state.is_empty() {
            tracing::debug!("All commands complete. Returning");
            return Ok(settled_commands);
        }

        delay_for(Duration::from_millis(1000)).await;

        let query: Vec<_> = state
            .iter()
            .map(|x| ["id__in".into(), x.to_string()])
            .chain(iter::once(["limit".into(), "0".into()]))
            .collect();

        let client = iml_manager_client::get_api_client()?;

        let cmds: ApiList<Command> =
            iml_manager_client::get(client, Command::endpoint_name(), query, None)
                .await?;

        for cmd in cmds.objects {
            if cmd_finished(&cmd) {
                state.remove(&cmd.id);

                if let Some(tx) = tx.as_ref() {
                    let _ = tx.unbounded_send(Progress::Complete(cmd.clone()));
                }

                settled_commands.push(cmd);
            } else if let Some(tx) = tx.as_ref() {
                let _ = tx.unbounded_send(Progress::Update(cmd.id));
            }
        }
    }
}

/// Waits for command completion and prints progress messages.
/// This will error on command failure and print failed commands in the error message.
pub async fn wait_for_cmds_success(
    cmds: &[Command],
    tx: Option<mpsc::UnboundedSender<Progress>>,
) -> Result<Vec<Command>, CmdUtilError> {
    let cmds = wait_for_cmds_progress(cmds, tx).await?;

    let (failed, passed): (Vec<_>, Vec<_>) =
        cmds.into_iter().partition(|x| x.errored || x.cancelled);

    if !failed.is_empty() {
        Err(failed.into())
    } else {
        Ok(passed)
    }
}

fn cmd_finished(cmd: &Command) -> bool {
    cmd.complete
}
