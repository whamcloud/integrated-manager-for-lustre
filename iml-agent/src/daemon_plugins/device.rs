// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
};
use async_trait::async_trait;
use device_types::{devices::Device, Command, Output as DeviceOutput};
use futures::{
    future, lock::Mutex, Future, FutureExt, Stream, StreamExt, TryFutureExt, TryStreamExt,
};
use std::{io, pin::Pin, sync::Arc};
use stream_cancel::{Trigger, Tripwire};
use tokio::{io::AsyncWriteExt, net::UnixStream};
use tokio_util::codec::{FramedRead, LinesCodec};

/// Opens a persistent stream to device scanner.
fn device_stream() -> impl Stream<Item = Result<String, ImlAgentError>> {
    UnixStream::connect("/var/run/device-scanner.sock")
        .err_into()
        .and_then(|mut conn| async {
            conn.write_all(b"\"Stream\"\n")
                .err_into::<ImlAgentError>()
                .await?;

            Ok(conn)
        })
        .map_ok(|c| FramedRead::new(c, LinesCodec::new()).err_into())
        .try_flatten_stream()
}

#[derive(Debug, Eq, PartialEq)]
enum Status {
    Pending,
    Sent,
}

#[derive(Debug)]
struct State {
    device: Option<Device>,
    command_buffer: Vec<Command>,
    status: Status,
}

pub fn create() -> impl DaemonPlugin {
    Devices {
        trigger: None,
        state: Arc::new(Mutex::new(State {
            device: None,
            command_buffer: Vec::new(),
            status: Status::Sent,
        })),
    }
}

#[derive(Debug)]
pub struct Devices {
    trigger: Option<Trigger>,
    state: Arc<Mutex<State>>,
}

#[async_trait]
impl DaemonPlugin for Devices {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let (trigger, tripwire) = Tripwire::new();

        self.trigger = Some(trigger);

        let fut = device_stream()
            .boxed()
            .and_then(|x| future::ready(serde_json::from_str(&x)).err_into())
            .into_future();

        let state = Arc::clone(&self.state);

        Box::pin(async move {
            let (x, s) = fut.await;

            let x: Output = match x {
                Some(x) => x,
                None => {
                    return Err(ImlAgentError::Io(io::Error::new(
                        io::ErrorKind::ConnectionAborted,
                        "Device scanner connection aborted before any data was sent",
                    )))
                }
            }?;

            {
                let mut state = state.lock().await;

                x.map(|x| {
                    let values: Vec<_> = serde_json::from_value(x).unwrap();
                    for v in values {
                        match v {
                            DeviceOutput::Device(d) => state.device = Some(d),
                            DeviceOutput::Command(c) => state.command_buffer.push(c),
                        }
                    }
                });
            }

            {
                let state = state.clone();
                tokio::spawn(
                    s.take_until(tripwire)
                        .try_for_each(move |x| {
                            let state = Arc::clone(&state);

                            async move {
                                let mut state = state.lock().await;

                                tracing::debug!("marking pending (is none: {}) ", x.is_none());

                                state.status = Status::Pending;
                                x.map(|x| {
                                    let values: Vec<_> = serde_json::from_value(x).unwrap();
                                    for v in values {
                                        match v {
                                            DeviceOutput::Device(d) => state.device = Some(d),
                                            DeviceOutput::Command(c) => {
                                                state.command_buffer.push(c)
                                            }
                                        }
                                    }
                                });

                                tracing::debug!(
                                    "{} items buffered after push",
                                    state.command_buffer.len()
                                );

                                Ok(())
                            }
                        })
                        .map(|x| {
                            if let Err(e) = x {
                                tracing::error!("Error processing device output: {}", e);
                            }
                        }),
                );
            }

            {
                let mut state = state.lock().await;

                tracing::debug!(
                    "Device is some: {}, {} items buffered before send (in create_session)",
                    state.device.is_some(),
                    state.command_buffer.len()
                );
                let buffer = std::mem::replace(&mut state.command_buffer, Vec::new());
                let to_be_sent = (state.device.take().unwrap(), buffer);

                let serialized = serde_json::to_value(&to_be_sent).unwrap();
                Ok(Some(serialized))
            }
        })
    }
    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let mut state = state.lock().await;

            if state.status == Status::Pending {
                tracing::debug!("Sending new value");
                state.status = Status::Sent;

                tracing::debug!(
                    "Device is some: {}, {} items buffered before send (in create_session)",
                    state.device.is_some(),
                    state.command_buffer.len()
                );
                let buffer = std::mem::replace(&mut state.command_buffer, Vec::new());
                let to_be_sent = (state.device.take().unwrap(), buffer);

                let serialized = serde_json::to_value(&to_be_sent).unwrap();
                Ok(Some(serialized))
            } else {
                Ok(None)
            }
        }
        .boxed()
    }
    async fn teardown(&mut self) -> Result<(), ImlAgentError> {
        self.trigger.take();

        Ok(())
    }
}
