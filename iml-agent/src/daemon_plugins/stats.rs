// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
};
use futures::{future, Future, FutureExt};
use iml_cmd::{CheckedCommandExt, Command};
use lustre_collector::{parse_lctl_output, parse_lnetctl_output, parser};
use std::{pin::Pin, str};

pub fn create() -> impl DaemonPlugin {
    Stats
}

#[derive(Debug)]
struct Stats;

impl DaemonPlugin for Stats {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        self.update_session()
    }
    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        async {
            let mut cmd1 = Command::new("lctl");
            let cmd1 = cmd1
                .arg("get_param")
                .args(parser::params())
                .checked_output();

            let mut cmd2 = Command::new("lnetctl");
            let cmd2 = cmd2.arg("export").checked_output();

            let (x, y) = future::try_join(cmd1, cmd2).await?;

            let lctl_output = parse_lctl_output(&x.stdout)?;

            let lnetctl_stats = str::from_utf8(&y.stdout)?;

            let lnetctl_output = parse_lnetctl_output(lnetctl_stats)?;

            let out = serde_json::to_value(&vec![lctl_output, lnetctl_output])?;

            Ok(Some(out))
        }
        .boxed()
    }
}
