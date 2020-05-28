// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{display_utils, error::ImlManagerCliError};
use futures::{future, FutureExt, TryFutureExt};
use iml_api_utils::dependency_tree::{Rich, Deps};
use iml_wire_types::{ApiList, AvailableAction, Command, EndpointName, FlatQuery, Host, Job};
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::sync::Arc;
use std::{collections::HashMap, fmt::Debug, iter, time::Duration};
use tokio::{task::spawn_blocking, time::delay_for};
use regex::{Captures, Regex};

type Job0 = Job<Option<serde_json::Value>>;
type RichCommand = Rich<i32, Arc<Command>>;
type RichJob = Rich<i32, Arc<Job0>>;

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

fn job_finished(job: &Job<Option<serde_json::Value>>) -> bool {
    // job.state can be "pending", "tasked" or "complete"
    // if a job is errored or cancelled, it is also complete
    job.state == "complete"
}

pub async fn wait_for_cmd(cmd: Command) -> Result<Command, ImlManagerCliError> {
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
pub async fn wait_for_cmds(cmds: &[Command]) -> Result<Vec<Command>, ImlManagerCliError> {
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

    let mut settled_commands = vec![];

    let fut = spawn_blocking(move || m.join())
        .map(|x| x.map_err(|e| e.into()).and_then(std::convert::identity));

    let mut commands: HashMap<i32, Rich<i32, Command>> = HashMap::new();
    let mut jobs: HashMap<i32, Rich<i32, Job0>> = HashMap::new();

    let fut2 = async {
        loop {
            if cmd_spinners.is_empty() {
                tracing::debug!("All commands complete. Returning");
                return Ok::<_, ImlManagerCliError>(());
            }

            delay_for(Duration::from_millis(1000)).await;

            let query: Vec<_> = cmd_spinners
                .keys()
                .map(|x| ["id__in".into(), x.to_string()])
                .chain(iter::once(["limit".into(), "0".into()]))
                .collect();

            let cmds: ApiList<Command> = get(Command::endpoint_name(), query).await?;

            let new_cmds: HashMap<i32, Rich<i32, Command>> = cmds
                .objects
                .into_iter()
                .map(|t| {
                    let (id, deps) = extract_children_from_cmd(&t);
                    (id, Rich { id, deps, inner: t })
                })
                .collect();
            commands.extend(new_cmds);

            for cmd in commands.values() {
                if cmd_finished(&cmd) {
                    let pb = cmd_spinners.remove(&cmd.id).unwrap();
                    pb.finish_with_message(&display_utils::format_cmd_state(&cmd));
                    settled_commands.push(cmd.clone());
                } else {
                    let pb = cmd_spinners.get(&cmd.id).unwrap();
                    pb.inc(1);
                }
            }

            let load_job_ids = cmd_spinners
                .keys()
                .filter(|c| commands.contains_key(c))
                .flat_map(|c| commands[c].deps())
                .filter(|j| jobs.contains_key(j))
                .filter(|j| !job_finished(&jobs[*j]))
                .copied()
                .collect::<Vec<i32>>();
        }
    };

    future::try_join(fut.err_into(), fut2).await?;

    Ok(settled_commands.into_iter().map(|rc| rc.inner).collect())
}

/// Waits for command completion and prints progress messages.
/// This will error on command failure and print failed commands in the error message.
pub async fn wait_for_cmds_success(cmds: &[Command]) -> Result<Vec<Command>, ImlManagerCliError> {
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
) -> Result<ApiList<AvailableAction>, ImlManagerCliError> {
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
pub fn first<T: EndpointName>(x: ApiList<T>) -> Result<T, ImlManagerCliError> {
    x.objects
        .into_iter()
        .next()
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
    get(Host::endpoint_name(), Host::query()).await
}

pub async fn get_all<T: EndpointName + FlatQuery + Debug + serde::de::DeserializeOwned>(
) -> Result<ApiList<T>, ImlManagerCliError> {
    get(T::endpoint_name(), T::query()).await
}

pub async fn get_one<T: EndpointName + FlatQuery + Debug + serde::de::DeserializeOwned>(
    query: Vec<(&str, &str)>,
) -> Result<T, ImlManagerCliError> {
    let mut q = T::query();
    q.extend(query);
    first(get(T::endpoint_name(), q).await?)
}

pub async fn get_influx<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    db: &str,
    influxql: &str,
) -> Result<T, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;

    iml_manager_client::get_influx(client, db, influxql)
        .await
        .map_err(|e| e.into())
}

fn extract_children_from_cmd(cmd: &Command) -> (i32, Vec<i32>) {
    let mut deps = cmd
        .jobs
        .iter()
        .filter_map(|s| extract_uri_id::<Job0>(s))
        .collect::<Vec<i32>>();
    deps.sort();
    (cmd.id, deps)
}

fn extract_uri_id<T: EndpointName>(input: &str) -> Option<i32> {
    lazy_static::lazy_static! {
        static ref RE: Regex = Regex::new(r"/api/(\w+)/(\d+)/").unwrap();
    }
    RE.captures(input).and_then(|cap: Captures| {
        let s = cap.get(1).unwrap().as_str();
        let t = cap.get(2).unwrap().as_str();
        if s == T::endpoint_name() {
            t.parse::<i32>().ok()
        } else {
            None
        }
    })
}

mod tests {
    use super::*;
    use iml_wire_types::Command;

    #[test]
    fn test_simple() {
        assert_eq!(extract_uri_id::<Command>("/api/command/123/"), Some(123));
    }
}