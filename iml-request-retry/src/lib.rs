// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;

use std::fmt::Debug;
use std::time::Duration;
use tokio::timer::delay_for;
use tracing;

pub mod policy;

/// There is one important requirement one needs to take in account when working with Rust futures:
/// - Once a future has finished, clients should not poll it again.
///   https://doc.rust-lang.org/std/future/trait.Future.html#panics
/// Therefore when the future returned `Err(something)`, we must _recreate_ it to await again.
///
/// Hence, given a future of type `F` we need to pass the thunk `Fn() -> F`, and the trait
/// `FutureFactory` is the typed abstraction over such thunks.
pub trait FutureFactory<T, E, F>
where
    F: Future<Output = Result<T, E>>,
{
    fn build_future(&self) -> F;
}

/// Render a function Fn() -> Future<Output=...> to have FutureFactory
impl<T, E, F, FF> FutureFactory<T, E, F> for FF
where
    F: Future<Output = Result<T, E>>,
    FF: Fn() -> F,
{
    fn build_future(&self) -> F {
        (*self)()
    }
}

/// Retry policy is a function or an object, that for every request tells us, whether
/// it is needed to
/// - perform immediate retry attempt to send the request again
/// - or wait some
pub trait RetryPolicy<E: Debug> {
    fn on_ok(&mut self, _: u32) {}
    fn on_err(&mut self, _: u32, _: E) -> RetryAction<E>;
}

/// Used as a result in the `RetryPolicy::on_err`
#[derive(Debug, Clone, PartialEq)]
pub enum RetryAction<E: Debug> {
    RetryNow,
    WaitFor(Duration),
    ReturnError(E),
}

/// render a function as the error handler
impl<P, E: Debug> RetryPolicy<E> for P
where
    P: FnMut(u32, E) -> RetryAction<E>,
{
    fn on_err(&mut self, k: u32, e: E) -> RetryAction<E> {
        (*self)(k, e)
    }
}

/// *NOTE*: (dyn RetryPolicy<E> + Send) is needed, otherwise we have
/// error[E0277]: `dyn iml_request_retry::RetryPolicy<reqwest::error::Error>` cannot be sent between threads safely
/// in the example. See `examples/demo-server-client.rs` and try to compile the example with the signature without `Send`:
/// `pub async fn retry_future(..., policy: &mut dyn RetryPolicy<E>) ...`
pub async fn retry_future<T, E, F, FF>(
    factory: FF,
    policy: &mut (dyn RetryPolicy<E> + Send),
) -> Result<T, E>
where
    E: Debug,
    F: Future<Output = Result<T, E>>,
    FF: FutureFactory<T, E, F>,
{
    let mut request_no = 0u32;
    loop {
        let future = factory.build_future();
        tracing::debug!("about to call the future built");
        match future.await {
            Ok(x) => {
                policy.on_ok(request_no);
                return Ok(x);
            }
            Err(e) => {
                let action = policy.on_err(request_no, e);
                tracing::debug!("on request: {} => action: {:?}", request_no, action);
                match action {
                    RetryAction::RetryNow => { /* do nothing, iterate again */ }
                    RetryAction::WaitFor(duration) => delay_for(duration).await,
                    RetryAction::ReturnError(err) => return Err(err),
                }
            }
        }
        request_no += 1
    }
}

pub async fn retry_future_gen<T, E, F, FF, P>(factory: FF, policy: P) -> Result<T, E>
where
    E: Debug,
    F: Future<Output = Result<T, E>>,
    P: Fn(u32, E) -> RetryAction<E>,
    FF: FutureFactory<T, E, F>,
{
    let mut request_no = 0u32;
    loop {
        let future = factory.build_future();
        tracing::debug!("about to call the future built");
        match future.await {
            Ok(x) => {
                // just silently return Ok(x), when policy is immutable
                return Ok(x);
            }
            Err(e) => {
                let action = policy(request_no, e);
                tracing::debug!("on request: {} => action: {:?}", request_no, action);
                match action {
                    RetryAction::RetryNow => { /* do nothing, iterate again */ }
                    RetryAction::WaitFor(duration) => delay_for(duration).await,
                    RetryAction::ReturnError(err) => return Err(err),
                }
            }
        }
        request_no += 1
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use futures::executor::block_on;
    use futures::future::{err, ok};
    use std::cell::Cell;

    #[derive(Debug, Clone, PartialEq)]
    enum Error {
        Fatal,
        NonFatal,
    }

    #[derive(Clone)]
    struct Futures<F> {
        index: Cell<usize>,
        futures: Vec<F>,
    }

    impl<T, E, F> FutureFactory<T, E, F> for Futures<F>
    where
        F: Future<Output = Result<T, E>> + Clone,
    {
        fn build_future(&self) -> F {
            let i = self.index.get();
            self.index.set(i + 1);
            self.futures[i].clone()
        }
    }

    #[test]
    fn simple() {
        let policy = |_, _| RetryAction::RetryNow;
        let factory = Futures {
            index: Cell::new(0),
            futures: vec![err(Error::Fatal), ok(42)],
        };
        assert_eq!(Ok(42), block_on(retry_future_gen(factory, &policy)));
    }

    #[test]
    fn return_error() {
        let policy = |_, e| match e {
            Error::NonFatal => RetryAction::RetryNow,
            Error::Fatal => RetryAction::ReturnError(e),
        };
        let factory = Futures {
            index: Cell::new(0),
            futures: vec![err(Error::NonFatal), err(Error::Fatal), ok(42)],
        };
        assert_eq!(
            Err(Error::Fatal),
            block_on(retry_future_gen(factory, &policy))
        );
    }
}
