// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::EmfAgentError,
    daemon_plugins::{DaemonPlugin, Output},
};
use emf_cmd::Command;
use futures::{future, Future, FutureExt, StreamExt, TryFutureExt, TryStreamExt};
use lustre_collector::{
    parse_cpustats_output, parse_lctl_output, parse_lnetctl_output, parse_meminfo_output, parser,
};
use std::{io, pin::Pin, str};

pub fn create() -> impl DaemonPlugin {
    Stats
}

fn params() -> Vec<String> {
    parser::params()
        .into_iter()
        .filter(|x| x != "obdfilter.*OST*.job_stats")
        .collect()
}

#[derive(Debug, Clone)]
struct Stats;

impl DaemonPlugin for Stats {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, EmfAgentError>> + Send>> {
        self.update_session()
    }
    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, EmfAgentError>> + Send>> {
        async {
            let mut cmd1 = Command::new("lctl");
            let cmd1 = cmd1
                .arg("get_param")
                .args(params())
                .kill_on_drop(true)
                .output()
                .err_into();

            let mut cmd2 = Command::new("lnetctl");
            let cmd2 = cmd2.arg("export").kill_on_drop(true).output().err_into();

            let cmd3 = emf_fs::read_file_to_end("/proc/meminfo").err_into();

            let mut cmd4 = emf_fs::stream_file_lines("/proc/stat").boxed();
            let cmd4 = cmd4.try_next().err_into();

            let result = future::try_join4(cmd1, cmd2, cmd3, cmd4).await;

            match result {
                Ok((lctl, lnetctl, meminfo, maybe_cpustats)) => {
                    let mut lctl_output = parse_lctl_output(&lctl.stdout)?;

                    let lnetctl_stats = str::from_utf8(&lnetctl.stdout)?;

                    let mut lnetctl_output = parse_lnetctl_output(lnetctl_stats)?;

                    lctl_output.append(&mut lnetctl_output);

                    let mut mem_output = parse_meminfo_output(&meminfo)?;

                    lctl_output.append(&mut mem_output);

                    if let Some(z) = maybe_cpustats {
                        let mut cpu_output = parse_cpustats_output(&z.trim().as_bytes())?;

                        lctl_output.append(&mut cpu_output);
                    }

                    let out = serde_json::to_value(&lctl_output)?;

                    Ok(Some(out))
                }
                Err(EmfAgentError::Io(ref err)) if err.kind() == io::ErrorKind::NotFound => {
                    tracing::debug!("Program was not found; will not send report.");

                    Ok(None)
                }
                Err(e) => Err(e),
            }
        }
        .boxed()
    }
}

#[cfg(test)]
mod tests {

    #[test]
    fn test_no_job_stats() {
        let xs = super::params();

        insta::assert_debug_snapshot!(xs);
    }
}
