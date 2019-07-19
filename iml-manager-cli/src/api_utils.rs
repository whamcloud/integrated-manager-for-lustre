// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::manager_cli_error::ImlManagerCliError;
use futures::{
    future::{self, loop_fn, Either, Loop},
    Future,
};
use iml_wire_types::Command;
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
