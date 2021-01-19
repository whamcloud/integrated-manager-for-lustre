// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    channel::oneshot,
    future::{self, Either},
    lock::Mutex,
    FutureExt,
};
use std::{
    collections::VecDeque,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::time::delay_for;

type State = Arc<Mutex<VecDeque<Vec<u8>>>>;

/// Takes a `VecDeque` and waits a given `Duration` until it has at least one message.
/// If messages are found, they are returned in a `Vec`.
/// If messages are not found by `timeout` an empty `Vec` is returned.
pub async fn flush(
    xs: State,
    timeout: Duration,
    terminated: oneshot::Receiver<Vec<Vec<u8>>>,
) -> Result<Vec<Vec<u8>>, oneshot::Canceled> {
    let timeout = Instant::now() + timeout;

    let fut = async {
        loop {
            if Instant::now() >= timeout {
                tracing::trace!("flush timed out");
                return Ok::<Vec<Vec<u8>>, oneshot::Canceled>(vec![]);
            }

            let drained = {
                let mut queue = xs.lock().await;
                queue.drain(..).collect::<Vec<_>>()
            };

            if drained.is_empty() {
                delay_for(Duration::from_millis(100)).await;
            } else {
                tracing::debug!("flush returning {} items", drained.len());

                return Ok::<Vec<Vec<u8>>, oneshot::Canceled>(drained);
            }
        }
    };

    futures::pin_mut!(fut);

    future::select(terminated, fut)
        .map(Either::factor_first)
        .await
        .0
}
