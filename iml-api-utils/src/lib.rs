// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future, FutureExt, TryFutureExt};
use iml_manager_client::{get, Client};
use iml_wire_types::{ApiList, AvailableAction, Command, EndpointName, FlatQuery, Host};
use lazy_static::lazy_static;
use regex::Regex;
use std::collections::HashSet;
use std::{collections::HashMap, fmt::Debug, iter, time::Duration};
use tokio::{task::spawn_blocking, time::delay_for};

/// Given a resource_uri, attempts to parse the id from it
pub fn extract_id(s: &str) -> Option<&str> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"^/?api/[^/]+/(\d+)/?$").unwrap();
    }
    let x = RE.captures(s)?;

    x.get(1).map(|x| x.as_str())
}

#[derive(Debug, thiserror::Error)]
pub enum CommandError {
    #[error(transparent)]
    ApiError(#[from] String),
    #[error(transparent)]
    ClientRequestError(#[from] iml_manager_client::ImlManagerClientError),
    #[error(transparent)]
    DoesNotExist(&'static str),
    #[error("Command failed")]
    FailedCommandError(#[from] Vec<Command>),
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

fn cmd_finished(cmd: &Command) -> bool {
    cmd.complete
}

pub async fn wait_for_cmds(cmds: &[Command]) -> Result<Vec<Command>, CommandError> {
    let mut in_progress_commands = HashSet::new();

    for cmd in cmds {
        in_progress_commands.insert(cmd.id);
    }

    let mut settled_commands = vec![];

    let fut2 = async {
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

            let client: Client = iml_manager_client::get_client().unwrap();

            let cmds: ApiList<Command> = get(client, Command::endpoint_name(), query).await?;

            for cmd in cmds.objects {
                if cmd_finished(&cmd) {
                    in_progress_commands.remove(&cmd.id);
                    settled_commands.push(cmd);
                }
            }
        }
    };

    fut2.await?;

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
