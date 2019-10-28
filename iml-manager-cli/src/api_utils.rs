// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{display_utils, error::ImlManagerCliError};
use futures::{future, TryFutureExt};
use iml_wire_types::{ApiList, Command, EndpointName, Host};
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::{
    collections::HashMap,
    iter,
    time::{Duration, Instant},
};
use tokio::timer::delay;
use tokio_executor::blocking::run;

#[derive(serde::Deserialize, Debug)]
pub struct CmdWrapper {
    pub command: Command,
}

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
) -> Result<Command, ImlManagerCliError> {
    let resp = post(Command::endpoint_name(), cmd_body).await?;

    let cmd = resp
        .json()
        .await?;

    tracing::debug!("Resp JSON is {:?}", cmd);

    Ok(cmd)
}

fn cmd_finished(cmd: &Command) -> bool {
    cmd.errored || cmd.cancelled || cmd.complete
}

pub async fn wait_for_cmd(cmd: Command) -> Result<Command, ImlManagerCliError> {
    loop {
        if cmd_finished(&cmd) {
            return Ok(cmd);
        }

        let when = Instant::now() + Duration::from_millis(1000);

        delay(when).await;

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

pub async fn wait_for_cmds(cmds: Vec<Command>) -> Result<Vec<Command>, ImlManagerCliError> {
    let m = MultiProgress::new();

    let num_cmds = cmds.len() as u64;

    let spinner_style = ProgressStyle::default_spinner()
        .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈ ")
        .template("{prefix:.bold.dim} {spinner} {wide_msg}");

    let mut cmd_spinners = HashMap::new();

    for (idx, cmd) in cmds.iter().enumerate() {
        let pb = m.add(ProgressBar::new(100000));
        pb.set_style(spinner_style.clone());
        pb.set_prefix(&format!("[{}/{}]", idx + 1, num_cmds));
        pb.set_message(&format!("{}", cmd.message));
        cmd_spinners.insert(cmd.id, pb);
    }

    let fut = run(move || m.join());

    let fut2 = async {
        loop {
            if cmd_spinners.len() == 0 {
                tracing::debug!("All commands complete. Returning");
                return Ok::<_, ImlManagerCliError>(());
            }

            let when = Instant::now() + Duration::from_millis(1000);

            delay(when).await;

            let query: Vec<_> = cmd_spinners
                .keys()
                .map(|x| ["id__in".into(), x.to_string()])
                .chain(iter::once(["limit".into(), "0".into()]))
                .collect();

            let cmds: ApiList<Command> = get(Command::endpoint_name(), query).await?;

            for cmd in cmds.objects {
                if cmd_finished(&cmd) {
                    let pb = cmd_spinners.remove(&cmd.id).unwrap();
                    pb.finish_with_message(&display_utils::format_cmd_state(&cmd));
                } else {
                    let pb = cmd_spinners.get(&cmd.id).unwrap();
                    pb.inc(1);
                }
            }
        }
    };

    future::try_join(fut.err_into(), fut2).await?;

    Ok(cmds)
}

/// Given an `ApiList`, this fn returns the first item or errors.
pub fn first<T: EndpointName>(x: ApiList<T>) -> Result<T, ImlManagerCliError> {
    x.objects
        .into_iter()
        .nth(0)
        .ok_or_else(|| ImlManagerCliError::DoesNotExist(T::endpoint_name()))
}

/// Wrapper for a `GET` to the Api.
pub async fn get<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    endpoint: &str,
    query: impl serde::Serialize,
) -> Result<T, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;

    iml_manager_client::get(client, endpoint, query)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `POST` to the Api.
pub async fn post(
    endpoint: &str,
    body: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;

    iml_manager_client::post(client, endpoint, body)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `PUT` to the Api.
pub async fn put(
    endpoint: &str,
    body: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;
    iml_manager_client::put(client, endpoint, body)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `DELETE` to the Api.
pub async fn delete(
    endpoint: &str,
    query: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client().expect("Could not create API client");
    iml_manager_client::delete(client, endpoint, query)
        .await
        .map_err(|e| e.into())
}

pub async fn get_hosts() -> Result<ApiList<Host>, ImlManagerCliError> {
    get(Host::endpoint_name(), serde_json::json!({"limit": 0})).await
}
