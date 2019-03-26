// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    future::{self, loop_fn, Loop},
    prelude::*,
};
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tokio::timer::Delay;

type State = Arc<Mutex<VecDeque<Vec<u8>>>>;

type LoopState = Loop<Vec<Vec<u8>>, State>;

/// Takes a `VecDeque` and waits a given `Duration` until it has at least one message.
/// If messages are found, they are returned in a `Vec`.
/// If messages are not found by `timeout` an empty `Vec` is returned.
pub fn flush(
    xs: State,
    timeout: Duration,
) -> impl Future<Item = Vec<Vec<u8>>, Error = failure::Error> {
    let timeout = Instant::now() + timeout;

    loop_fn(
        xs,
        move |xs| -> Box<Future<Item = LoopState, Error = failure::Error> + Send> {
            if Instant::now() >= timeout {
                log::debug!("flush timed out");
                return Box::new(future::ok(Loop::Break(vec![])));
            }

            let drained = {
                let mut queue = xs.lock().unwrap();
                queue.drain(..).collect::<Vec<_>>()
            };

            if drained.is_empty() {
                let when = Instant::now() + Duration::from_millis(500);

                Box::new(
                    Delay::new(when)
                        .map_err(failure::Error::from)
                        .map(move |_| Loop::Continue(xs)),
                )
            } else {
                log::debug!("flush returning {:?} items", drained.len());
                Box::new(future::ok(Loop::Break(drained)))
            }
        },
    )
}
