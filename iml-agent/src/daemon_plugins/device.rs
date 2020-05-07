// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
};
use async_trait::async_trait;
use futures::{
    future, lock::Mutex, Future, FutureExt, Stream, StreamExt, TryFutureExt, TryStreamExt,
};
use std::{io, pin::Pin, sync::Arc};
use stream_cancel::{StreamExt as _, Trigger, Tripwire};
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

#[derive(Eq, PartialEq)]
enum State {
    Pending,
    Sent,
}

pub fn create() -> impl DaemonPlugin {
    Devices {
        trigger: None,
        state: Arc::new(Mutex::new((None, State::Sent))),
    }
}

#[derive(Debug)]
pub struct Devices {
    trigger: Option<Trigger>,
    state: Arc<Mutex<(Output, State)>>,
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
                let mut lock = state.lock().await;

                lock.0 = x.clone();
            }

            tokio::spawn(
                s.take_until(tripwire)
                    .try_for_each(move |x| {
                        let state = Arc::clone(&state);

                        async move {
                            let mut lock = state.lock().await;

                            if lock.0 != x {
                                tracing::debug!("marking pending (is none: {}) ", x.is_none());

                                lock.0 = x;
                                lock.1 = State::Pending;
                            }

                            Ok(())
                        }
                    })
                    .map(|x| {
                        if let Err(e) = x {
                            tracing::error!("Error processing device output: {}", e);
                        }
                    }),
            );

            Ok(x)
        })
    }
    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let mut lock = state.lock().await;

            if lock.1 == State::Pending {
                tracing::debug!("Sending new value");
                lock.1 = State::Sent;

                Ok(lock.0.clone())
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
