// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_client::{get, Client};
use iml_wire_types::{ApiList, Command, EndpointName};
use std::collections::HashSet;
use std::{fmt::Debug, iter, time::Duration};
use tokio::time::delay_for;

#[derive(Debug, thiserror::Error)]
pub enum CommandError {
    #[error("API Error")]
    ApiError(String),
    #[error(transparent)]
    ClientRequestError(#[from] iml_manager_client::ImlManagerClientError),
    #[error("Does Not Exist")]
    DoesNotExist(&'static str),
    #[error("Command failed")]
    FailedCommandError(Vec<Command>),
    #[error(transparent)]
    FromUtf8Error(#[from] std::string::FromUtf8Error),
    #[error(transparent)]
    ImlGraphqlQueriesErrors(#[from] iml_graphql_queries::Errors),
    #[error(transparent)]
    IntParseError(#[from] std::num::ParseIntError),
    #[error(transparent)]
    IoError(#[from] std::io::Error),
    #[error(transparent)]
    TokioJoinError(#[from] tokio::task::JoinError),
    #[error(transparent)]
    TokioTimerError(#[from] tokio::time::Error),
}

impl From<Vec<Command>> for CommandError {
    fn from(xs: Vec<Command>) -> Self {
        CommandError::FailedCommandError(xs)
    }
}

fn cmd_finished(cmd: &Command) -> bool {
    cmd.complete
}

pub async fn wait_for_cmds(cmds: &[Command]) -> Result<Vec<Command>, CommandError> {
    let mut in_progress_commands = HashSet::new();

    for cmd in cmds {
        in_progress_commands.insert(cmd.id);
    }

    let mut settled_commands = vec![];

    let fut = async {
        loop {
            if in_progress_commands.is_empty() {
                tracing::debug!("All commands complete. Returning");
                return Ok::<_, CommandError>(());
            }

            delay_for(Duration::from_millis(1000)).await;

            let query: Vec<_> = in_progress_commands
                .iter()
                .map(|x| ["id__in".into(), x.to_string()])
                .chain(iter::once(["limit".into(), "0".into()]))
                .collect();

            let client: Client = iml_manager_client::get_client()?;

            let cmds: ApiList<Command> = get(client, Command::endpoint_name(), query).await?;

            for cmd in cmds.objects {
                if cmd_finished(&cmd) {
                    in_progress_commands.remove(&cmd.id);
                    settled_commands.push(cmd);
                }
            }
        }
    };

    fut.await?;

    Ok(settled_commands)
}

/// Waits for command completion and prints progress messages.
/// This will error on command failure and print failed commands in the error message.
pub async fn wait_for_cmds_success(cmds: &[Command]) -> Result<Vec<Command>, CommandError> {
    let cmds = wait_for_cmds(cmds).await?;

    let (failed, passed): (Vec<_>, Vec<_>) =
        cmds.into_iter().partition(|x| x.errored || x.cancelled);

    if !failed.is_empty() {
        Err(failed.into())
    } else {
        Ok(passed)
    }
}
