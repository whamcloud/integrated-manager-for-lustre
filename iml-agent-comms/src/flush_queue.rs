// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    future::{self, loop_fn, Either, Loop},
    Future,
};
use parking_lot::Mutex;
use std::{
    collections::VecDeque,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::timer::Delay;

type State = Arc<Mutex<VecDeque<Vec<u8>>>>;

/// Takes a `VecDeque` and waits a given `Duration` until it has at least one message.
/// If messages are found, they are returned in a `Vec`.
/// If messages are not found by `timeout` an empty `Vec` is returned.
pub fn flush(
    xs: State,
    timeout: Duration,
) -> impl Future<Item = Vec<Vec<u8>>, Error = failure::Error> {
    let timeout = Instant::now() + timeout;

    loop_fn(xs, move |xs| {
        if Instant::now() >= timeout {
            log::trace!("flush timed out");
            return Either::B(future::ok(Loop::Break(vec![])));
        }

        let drained = {
            let mut queue = xs.lock();
            queue.drain(..).collect::<Vec<_>>()
        };

        if drained.is_empty() {
            let when = Instant::now() + Duration::from_millis(500);

            Either::A(Delay::new(when).from_err().map(move |_| Loop::Continue(xs)))
        } else {
            log::debug!("flush returning {:?} items", drained.len());
            Either::B(future::ok(Loop::Break(drained)))
        }
    })
}
