// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_agent::{
    agent_error::EmfAgentError,
    device_scanner_client, env,
    util::{create_filtered_writer, UnboundedSenderExt},
};
use emf_cmd::Command;
use futures::{StreamExt, TryFutureExt, TryStreamExt};
use lustre_collector::{mgs::mgs_fs_parser, parse_mgs_fs_output, Record, TargetStats};
use serde_json::Value;
use std::io;

async fn get_mgs_fses() -> Result<Vec<String>, EmfAgentError> {
    let output = Command::new("lctl")
        .arg("get_param")
        .arg("-N")
        .args(mgs_fs_parser::params())
        .kill_on_drop(true)
        .output()
        .err_into()
        .await;

    let output = match output {
        Ok(x) => x,
        Err(EmfAgentError::Io(ref err)) if err.kind() == io::ErrorKind::NotFound => {
            tracing::debug!("lctl binary was not found; will not send mgs fs info.");

            return Ok(vec![]);
        }
        Err(e) => return Err(e),
    };

    let fses: Vec<_> = parse_mgs_fs_output(&output.stdout)
        .unwrap_or_default()
        .into_iter()
        .filter_map(|x| match x {
            Record::Target(TargetStats::FsNames(x)) => Some(x),
            _ => None,
        })
        .flat_map(|x| x.value)
        .map(|x| x.0)
        .collect();

    Ok(fses)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let port = env::get_port("DEVICE_AGENT_DEVICE_SERVICE_PORT");

    let writer = create_filtered_writer(port)?;
    let mut s = device_scanner_client::stream_lines(device_scanner_client::Cmd::Stream).boxed();

    while let Some(x) = s.try_next().await? {
        let x = serde_json::from_str(&x)?;

        let fses = get_mgs_fses().await?;
        let fses = serde_json::to_value(fses)?;

        let xs = Value::Array(vec![x, fses]);

        let _ = writer.send_msg(xs);
    }

    Ok(())
}
