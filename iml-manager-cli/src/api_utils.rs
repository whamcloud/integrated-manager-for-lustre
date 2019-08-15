// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::manager_cli_error::ImlManagerCliError;
use futures::{
    future::{self, loop_fn, Either, Loop},
    Future,
};
use iml_wire_types::{ApiList, Command, EndpointName};
use std::time::{Duration, Instant};
use tokio::timer::Delay;

#[derive(serde::Deserialize, Debug)]
pub struct CmdWrapper {
    pub command: Command,
}

/// Takes an asynchronous computation (Future), runs it to completion
/// and returns the result.
///
/// Even though the action is asynchronous, this fn will block until
/// the future resolves.
pub fn run_cmd<R: Send + 'static, E: Send + 'static>(
    fut: impl Future<Item = R, Error = E> + Send + 'static,
) -> std::result::Result<R, E> {
    tokio::runtime::Runtime::new().unwrap().block_on_all(fut)
}

fn cmd_finished(cmd: &Command) -> bool {
    cmd.errored || cmd.cancelled || cmd.complete
}

pub fn wait_for_cmd(cmd: Command) -> impl Future<Item = Command, Error = ImlManagerCliError> {
    loop_fn(cmd, move |cmd| {
        if cmd_finished(&cmd) {
            return Either::A(future::ok(Loop::Break(cmd)));
        }

        let when = Instant::now() + Duration::from_millis(1000);

        Either::B(
            Delay::new(when)
                .from_err()
                .and_then(move |_| {
                    let client =
                        iml_manager_client::get_client().expect("Could not create API client");
                    iml_manager_client::get(
                        client,
                        &format!("command/{}", cmd.id),
                        Vec::<(String, String)>::new(),
                    )
                    .from_err()
                })
                .map(Loop::Continue),
        )
    })
}

/// Given an `ApiList`, this fn returns the first item or errors.
pub fn first<T: EndpointName>(x: ApiList<T>) -> Result<T, ImlManagerCliError> {
    x.objects
        .into_iter()
        .nth(0)
        .ok_or_else(|| ImlManagerCliError::DoesNotExist(T::endpoint_name()))
}

/// Wrapper for a `GET` to the Api.
pub fn get<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    endpoint: &str,
    query: impl serde::Serialize,
) -> impl Future<Item = T, Error = ImlManagerCliError> {
    let client = iml_manager_client::get_client().expect("Could not create API client");

    iml_manager_client::get(client, endpoint, query).from_err()
}

/// Wrapper for a `POST` to the Api.
pub fn post(
    endpoint: &str,
    query: impl serde::Serialize,
) -> impl Future<
    Item = (iml_manager_client::Response, iml_manager_client::Chunk),
    Error = ImlManagerCliError,
> {
    let client = iml_manager_client::get_client().expect("Could not create API client");
    iml_manager_client::post(client, endpoint, query)
        .and_then(iml_manager_client::concat_body)
        .from_err()
}

/// Wrapper for a `DELETE` to the Api.
pub fn delete(
    endpoint: &str,
    query: impl serde::Serialize,
) -> impl Future<
    Item = (iml_manager_client::Response, iml_manager_client::Chunk),
    Error = ImlManagerCliError,
> {
    let client = iml_manager_client::get_client().expect("Could not create API client");
    iml_manager_client::delete(client, endpoint, query)
        .and_then(iml_manager_client::concat_body)
        .from_err()
}
