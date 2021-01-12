// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    display_utils::{self, display_cmd_state, wrap_fut},
    error::EmfManagerCliError,
};
use emf_command_utils::{wait_for_cmds_progress, Progress};
use emf_wire_types::{ApiList, AvailableAction, Command, EndpointName, FlatQuery, Host};
use futures::{channel::mpsc, future, FutureExt, StreamExt, TryFutureExt};
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::{collections::HashMap, fmt::Debug, time::Duration};
use tokio::{task::spawn_blocking, time::delay_for};

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

pub async fn create_command<T: serde::Serialize>(
    cmd_body: SendCmd<T>,
) -> Result<Command, EmfManagerCliError> {
    let resp = post(Command::endpoint_name(), cmd_body)
        .await?
        .error_for_status()?;

    let cmd = resp.json().await?;

    tracing::debug!("Resp JSON is {:?}", cmd);

    Ok(cmd)
}

fn cmd_finished(cmd: &Command) -> bool {
    cmd.complete
}

pub async fn wait_for_cmd(cmd: Command) -> Result<Command, EmfManagerCliError> {
    loop {
        if cmd_finished(&cmd) {
            return Ok(cmd);
        }

        delay_for(Duration::from_millis(1000)).await;

        let client = emf_manager_client::get_client()?;

        let cmd = emf_manager_client::get(
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

/// Waits for command completion and prints a spinner during progression.
/// When completed, prints the final command state
pub async fn wait_for_cmd_display(cmd: Command) -> Result<Command, EmfManagerCliError> {
    let cmd = wrap_fut(&cmd.message.to_string(), wait_for_cmd(cmd)).await?;

    display_cmd_state(&cmd);

    Ok(cmd)
}

/// Waits for command completion and prints progress messages
/// This *does not* error on command failure, it only tracks command
/// completion
pub async fn wait_for_cmds(cmds: &[Command]) -> Result<Vec<Command>, EmfManagerCliError> {
    let m = MultiProgress::new();

    let num_cmds = cmds.len() as u64;

    let spinner_style = ProgressStyle::default_spinner()
        .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈ ")
        .template("{prefix:.bold.dim} {spinner} {wide_msg}");

    let mut cmd_spinners = HashMap::new();

    for (idx, cmd) in cmds.iter().enumerate() {
        let pb = m.add(ProgressBar::new(100_000));
        pb.set_style(spinner_style.clone());
        pb.set_prefix(&format!("[{}/{}]", idx + 1, num_cmds));
        pb.set_message(&cmd.message);
        cmd_spinners.insert(cmd.id, pb);
    }

    let fut = spawn_blocking(move || m.join())
        .err_into::<EmfManagerCliError>()
        .map(|x| x.and_then(|x| x.map_err(|e| e.into())));

    let (tx, rx) = mpsc::unbounded();

    let fut2 = rx
        .fold(cmd_spinners, |mut cmd_spinners, x| {
            match x {
                Progress::Update(x) => {
                    let pb = cmd_spinners.get(&x).unwrap();
                    pb.inc(1);
                }
                Progress::Complete(x) => {
                    let pb = cmd_spinners.remove(&x.id).unwrap();
                    pb.finish_with_message(&display_utils::format_cmd_state(&x));
                }
            }

            future::ready(cmd_spinners)
        })
        .never_error()
        .err_into::<EmfManagerCliError>();

    let fut3 = wait_for_cmds_progress(cmds, Some(tx)).err_into::<EmfManagerCliError>();

    let (_, _, xs) = future::try_join3(fut, fut2, fut3).await?;

    Ok(xs)
}

/// Waits for command completion and prints progress messages.
/// This will error on command failure and print failed commands in the error message.
pub async fn wait_for_cmds_success(cmds: &[Command]) -> Result<Vec<Command>, EmfManagerCliError> {
    let cmds = wait_for_cmds(cmds).await?;

    let (failed, passed): (Vec<_>, Vec<_>) =
        cmds.into_iter().partition(|x| x.errored || x.cancelled);

    if !failed.is_empty() {
        Err(failed.into())
    } else {
        Ok(passed)
    }
}

pub async fn get_available_actions(
    id: u32,
    content_type_id: u32,
) -> Result<ApiList<AvailableAction>, EmfManagerCliError> {
    get(
        AvailableAction::endpoint_name(),
        vec![
            (
                "composite_ids",
                format!("{}:{}", content_type_id, id).as_ref(),
            ),
            ("limit", "0"),
        ],
    )
    .await
}

/// Given an `ApiList`, this fn returns the first item or errors.
pub fn first<T: EndpointName>(x: ApiList<T>) -> Result<T, EmfManagerCliError> {
    x.objects
        .into_iter()
        .next()
        .ok_or_else(|| EmfManagerCliError::DoesNotExist(T::endpoint_name()))
}

/// Wrapper for a `GET` to the Api.
pub async fn get<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    endpoint: &str,
    query: impl serde::Serialize,
) -> Result<T, EmfManagerCliError> {
    let client = emf_manager_client::get_client()?;

    emf_manager_client::get(client, endpoint, query)
        .await
        .map_err(|e| e.into())
}

pub async fn graphql<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    query: impl serde::Serialize + Debug,
) -> Result<T, EmfManagerCliError> {
    let client = emf_manager_client::get_client()?;

    emf_manager_client::graphql(client, query)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `POST` to the Api.
pub async fn post(
    endpoint: &str,
    body: impl serde::Serialize,
) -> Result<emf_manager_client::Response, EmfManagerCliError> {
    let client = emf_manager_client::get_client()?;

    emf_manager_client::post(client, endpoint, body)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `PUT` to the Api.
pub async fn put(
    endpoint: &str,
    body: impl serde::Serialize,
) -> Result<emf_manager_client::Response, EmfManagerCliError> {
    let client = emf_manager_client::get_client()?;
    emf_manager_client::put(client, endpoint, body)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `DELETE` to the Api.
pub async fn delete(
    endpoint: &str,
    query: impl serde::Serialize,
) -> Result<emf_manager_client::Response, EmfManagerCliError> {
    let client = emf_manager_client::get_client().expect("Could not create API client");
    emf_manager_client::delete(client, endpoint, query)
        .await
        .map_err(|e| e.into())
}

pub async fn get_hosts() -> Result<ApiList<Host>, EmfManagerCliError> {
    get(Host::endpoint_name(), Host::query()).await
}

pub async fn get_all<T: EndpointName + FlatQuery + Debug + serde::de::DeserializeOwned>(
) -> Result<ApiList<T>, EmfManagerCliError> {
    get(T::endpoint_name(), T::query()).await
}

pub async fn get_one<T: EndpointName + FlatQuery + Debug + serde::de::DeserializeOwned>(
    query: Vec<(&str, &str)>,
) -> Result<T, EmfManagerCliError> {
    let mut q = T::query();
    q.extend(query);
    first(get(T::endpoint_name(), q).await?)
}

pub async fn get_influx<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    db: &str,
    influxql: &str,
) -> Result<T, EmfManagerCliError> {
    let client = emf_manager_client::get_client()?;

    emf_manager_client::get_influx(client, db, influxql)
        .await
        .map_err(|e| e.into())
}
