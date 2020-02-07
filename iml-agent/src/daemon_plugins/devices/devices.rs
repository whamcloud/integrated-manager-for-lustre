// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{devices::flat_devices::process_tree, DaemonPlugin, Output},
};
use futures::{
    channel::oneshot, future, lock::Mutex, Future, FutureExt, Stream, StreamExt, TryFutureExt,
    TryStreamExt,
};
use std::{collections::BTreeMap, pin::Pin, sync::Arc};
use stream_cancel::{StreamExt as _, Trigger, Tripwire};
use tokio::{io::AsyncWriteExt, net::UnixStream};
use tokio_util::codec::{FramedRead, LinesCodec};

fn device_stream() -> impl Stream<Item = Result<String, ImlAgentError>> {
    UnixStream::connect("/var/run/device-scanner.sock")
        .err_into()
        .and_then(|mut conn| {
            async {
                conn.write_all(b"\"Stream\"\n")
                    .err_into::<ImlAgentError>()
                    .await?;

                Ok(conn)
            }
        })
        .map_ok(|c| FramedRead::new(c, LinesCodec::new()).err_into())
        .try_flatten_stream()
}

pub fn create() -> impl DaemonPlugin {
    Devices {
        trigger: None,
        state: Arc::new(Mutex::new((None, None))),
    }
}

#[derive(Debug)]
pub struct Devices {
    trigger: Option<Trigger>,
    state: Arc<Mutex<(Output, Output)>>,
}

impl DaemonPlugin for Devices {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let (trigger, tripwire) = Tripwire::new();
        let (tx, rx) = oneshot::channel();

        self.trigger = Some(trigger);

        let state = Arc::clone(&self.state);

        tokio::spawn(
            device_stream()
                .boxed()
                .and_then(|x| future::ready(serde_json::from_str(&x).map_err(|e| e.into())))
                .and_then(|x| {
                    let mut flat_devices = BTreeMap::new();

                    process_tree(&x, None, &mut flat_devices);

                    future::ready(
                        serde_json::to_value(flat_devices)
                            .map(Some)
                            .map_err(|e| e.into()),
                    )
                })
                .into_future()
                .then(|(x, s)| {
                    let x = if let Some(x) = x {
                        x.map(move |y| {
                            let _ = tx.send(y);
                            s
                        })
                    } else {
                        Ok(s)
                    };

                    future::ready(x)
                })
                .try_flatten_stream()
                .take_until(tripwire)
                .try_for_each(move |x| {
                    let state = Arc::clone(&state);

                    async move {
                        let mut s = state.lock().await;

                        s.0 = s.1.take();
                        s.1 = x;

                        Ok(())
                    }
                })
                .map(|x| {
                    if let Err(e) = x {
                        tracing::error!("Error processing device output: {}", e);
                    }
                }),
        );

        Box::pin(rx.err_into())
    }
    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let state = Arc::clone(&self.state);

        async move {
            let s = state.lock().await.clone();

            if s.0 != s.1 {
                Ok(s.1)
            } else {
                Ok(None)
            }
        }
        .boxed()
    }
    fn teardown(&mut self) -> Result<(), ImlAgentError> {
        self.trigger.take();

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use crate::daemon_plugins::devices::flat_devices::{process_tree, DeviceId, FlatDevices};
    use insta::assert_debug_snapshot;
    use serde_json;
    use std::fs;

    #[test]
    fn test_dev_tree_conversion() {
        use std::default::Default;
        let f = fs::read_to_string("./fixtures.json").unwrap();
        let x = serde_json::from_str(&f).unwrap();

        let id = DeviceId("none".to_string());

        let mut fds = FlatDevices::default();

        process_tree(&x, Some(id), &mut fds);

        assert_debug_snapshot!("flat_devices", fds);
    }
}
