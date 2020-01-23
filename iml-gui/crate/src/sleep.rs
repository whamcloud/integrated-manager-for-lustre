use futures::{
    channel::oneshot,
    future::{self, Either},
    Future, FutureExt,
};
use gloo_timers::future::TimeoutFuture;

/// Sleeps for the given duration and calls `complete_msg`
/// or calls `drop_msg` if the returned handle is dropped.
pub(crate) fn sleep_with_handle<Msg>(
    timeout: u32,
    complete_msg: Msg,
    drop_msg: Msg,
) -> (oneshot::Sender<()>, impl Future<Output = Result<Msg, Msg>>) {
    let (p, c) = oneshot::channel::<()>();

    let fut = future::select(c, TimeoutFuture::new(timeout)).map(move |either| match either {
        Either::Left((_, b)) => {
            drop(b);

            seed::log!("Timeout dropped");

            Ok(drop_msg)
        }
        Either::Right((_, _)) => Ok(complete_msg),
    });

    (p, fut)
}
