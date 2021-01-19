// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    channel::oneshot,
    future::{self, Either},
    Future, FutureExt,
};
use gloo_timers::future::TimeoutFuture;
use std::time::Duration;

/// Sleeps for the given duration and calls `complete_msg`
/// or calls `drop_msg` if the returned handle is dropped.
pub(crate) fn sleep_with_handle<Msg>(
    timeout: Duration,
    complete_msg: Msg,
    drop_msg: Msg,
) -> (oneshot::Sender<()>, impl Future<Output = Result<Msg, Msg>>) {
    let (p, c) = oneshot::channel::<()>();

    let fut = future::select(c, TimeoutFuture::new(timeout.as_millis() as u32)).map(move |either| match either {
        Either::Left((_, b)) => {
            drop(b);

            seed::log!("Timeout dropped");

            Ok(drop_msg)
        }
        Either::Right((_, _)) => Ok(complete_msg),
    });

    (p, fut)
}
