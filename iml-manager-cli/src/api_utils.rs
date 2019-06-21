// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{api_client, manager_cli_error::ImlManagerCliError};
use futures::{
    future::{self, loop_fn, Either, Loop},
    Future,
};
use iml_wire_types::Command;
use std::time::{Duration, Instant};
use tokio::timer::Delay;

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
                    let client = api_client::get_client().expect("Could not create API client");
                    api_client::get(client, &format!("command/{}", cmd.id))
                })
                .map(Loop::Continue),
        )
    })
}
