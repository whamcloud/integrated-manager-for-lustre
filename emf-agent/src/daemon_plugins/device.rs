// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::EmfAgentError,
    daemon_plugins::{DaemonPlugin, Output},
    device_scanner_client,
};
use async_trait::async_trait;
use emf_cmd::Command;
use futures::{future, lock::Mutex, Future, FutureExt, StreamExt, TryFutureExt, TryStreamExt};
use lustre_collector::{mgs::mgs_fs_parser, parse_mgs_fs_output, Record, TargetStats};
use serde_json::Value;
use std::{io, pin::Pin, sync::Arc};
use stream_cancel::{Trigger, Tripwire};

#[derive(Debug, Clone)]
pub struct Devices {
    trigger: Option<Arc<Trigger>>,
    state: Arc<Mutex<Output>>,
}

pub fn create() -> impl DaemonPlugin {
    Devices {
        trigger: None,
        state: Arc::new(Mutex::new(None)),
    }
}

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

#[async_trait]
impl DaemonPlugin for Devices {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, EmfAgentError>> + Send>> {
        let (trigger, tripwire) = Tripwire::new();

        self.trigger = Some(Arc::new(trigger));

        let fut = device_scanner_client::stream_lines(device_scanner_client::Cmd::Stream)
            .boxed()
            .and_then(|x| future::ready(serde_json::from_str(&x)).err_into())
            .into_future();

        let state = Arc::clone(&self.state);

        Box::pin(async move {
            let (x, s): (Option<Result<Value, EmfAgentError>>, _) = fut.await;

            let x: Value = match x {
                Some(x) => x?,
                None => {
                    return Err(EmfAgentError::Io(io::Error::new(
                        io::ErrorKind::ConnectionAborted,
                        "Device scanner connection aborted before any data was sent",
                    )))
                }
            };

            {
                state.lock().await.replace(x.clone());
            }

            tokio::spawn(
                s.take_until(tripwire)
                    .try_for_each(move |x| {
                        let state = Arc::clone(&state);

                        async move {
                            state.lock().await.replace(x);

                            Ok(())
                        }
                    })
                    .map(|x| {
                        if let Err(e) = x {
                            tracing::error!("Error processing device output: {}", e);
                        }
                    }),
            );

            let fses = get_mgs_fses().await?;
            let fses = serde_json::to_value(fses)?;

            let x = Some(Value::Array(vec![x, fses]));

            Ok(x)
        })
    }
    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, EmfAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let fses = get_mgs_fses().await?;
            let fses = serde_json::to_value(fses)?;

            let x = state
                .lock()
                .await
                .take()
                .map(|x| Value::Array(vec![x, fses]));

            Ok(x)
        }
        .boxed()
    }
    async fn teardown(&mut self) -> Result<(), EmfAgentError> {
        self.trigger.take();

        Ok(())
    }
}
