// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_client::{get, post, Client};
use iml_wire_types::{ApiList, Command, EndpointName};
use std::collections::HashSet;
use std::{fmt::Debug, iter, time::Duration};
use tokio::time::delay_for;

#[derive(serde::Serialize)]
pub struct SendJob<T> {
    pub class_name: String,
    pub args: T,
}

#[derive(serde::Serialize)]
pub struct SendCmd<T> {
    pub jobs: Vec<SendJob<T>>,
    pub message: String,
}

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
    ReqwestError(#[from] reqwest::Error),
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

pub async fn create_command<T: serde::Serialize>(
    cmd_body: SendCmd<T>,
) -> Result<Command, CommandError> {
    let client = iml_manager_client::get_client()?;
    let resp = post(client, Command::endpoint_name(), cmd_body)
        .await?
        .error_for_status()?;

    let cmd = resp.json().await?;

    tracing::debug!("Resp JSON is {:?}", cmd);

    Ok(cmd)
}

fn cmd_finished(cmd: &Command) -> bool {
    cmd.complete
}

pub async fn wait_for_cmd(cmd: Command) -> Result<Command, CommandError> {
    loop {
        if cmd_finished(&cmd) {
            return Ok(cmd);
        }

        delay_for(Duration::from_millis(1000)).await;

        let client = iml_manager_client::get_client()?;

        let cmd = iml_manager_client::get(
            client,
            &format!("command/{}", cmd.id),
            Vec::<(String, String)>::new(),
        )
        .await?;

        if cmd_finished(&cmd) {
            return Ok(cmd);
        }
    }
}

/// Waits for command completion and prints progress messages
/// This *does not* error on command failure, it only tracks command
/// completion
pub async fn wait_for_cmds(cmds: &[Command]) -> Result<Vec<Command>, CommandError> {
    #[cfg(feature = "cli")]
    let m = MultiProgress::new();

    #[cfg(feature = "cli")]
    let num_cmds = cmds.len() as u64;

    #[cfg(feature = "cli")]
    let spinner_style = ProgressStyle::default_spinner()
        .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈ ")
        .template("{prefix:.bold.dim} {spinner} {wide_msg}");

    #[cfg(not(feature = "cli"))]
    let mut in_progress_commands = HashSet::new();
    #[cfg(feature = "cli")]
    let mut cmd_spinners = HashMap::new();

    #[cfg(not(feature = "cli"))]
    for cmd in cmds {
        in_progress_commands.insert(cmd.id);
    }
    #[cfg(feature = "cli")]
    for (idx, cmd) in cmds.iter().enumerate() {
        let pb = m.add(ProgressBar::new(100_000));
        pb.set_style(spinner_style.clone());
        pb.set_prefix(&format!("[{}/{}]", idx + 1, num_cmds));
        pb.set_message(&cmd.message);
        cmd_spinners.insert(cmd.id, pb);
    }

    let mut settled_commands = vec![];

    let fut = async {
        loop {
            #[cfg(not(feature = "cli"))]
            if in_progress_commands.is_empty() {
                tracing::debug!("All commands complete. Returning");
                return Ok::<_, CommandError>(());
            }
            #[cfg(feature = "cli")]
            if cmd_spinners.is_empty() {
                tracing::debug!("All commands complete. Returning");
                return Ok::<_, ImlManagerCliError>(());
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
                #[cfg(not(feature = "cli"))]
                if cmd_finished(&cmd) {
                    in_progress_commands.remove(&cmd.id);
                    settled_commands.push(cmd);
                }
                #[cfg(feature = "cli")]
                if cmd_finished(&cmd) {
                    let pb = cmd_spinners.remove(&cmd.id).unwrap();
                    pb.finish_with_message(&display_utils::format_cmd_state(&cmd));
                    settled_commands.push(cmd);
                } else {
                    let pb = cmd_spinners.get(&cmd.id).unwrap();
                    pb.inc(1);
                }
            }
        }
    };

    #[cfg(feature = "cli")]
    let fut2 = spawn_blocking(move || m.join())
        .map(|x| x.map_err(|e| e.into()).and_then(std::convert::identity));

    #[cfg(not(feature = "cli"))]
    fut.await?;
    #[cfg(feature = "cli")]
    future::try_join(fut.err_into(), fut2).await?;

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
