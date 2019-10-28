// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlManagerCliError;
use iml_wire_types::{ApiList, Command, EndpointName};
use std::time::{Duration, Instant};
use tokio::timer::delay;

#[derive(serde::Deserialize, Debug)]
pub struct CmdWrapper {
    pub command: Command,
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
    query: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;

    iml_manager_client::post(client, endpoint, query)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `PUT` to the Api.
pub async fn put(
    endpoint: &str,
    query: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;
    iml_manager_client::put(client, endpoint, query)
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
