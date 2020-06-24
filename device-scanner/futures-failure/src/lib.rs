// Copyright (c) 2018 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use failure::Error;

pub mod stream_failure {
    use failure::{Error, Fail};
    use futures::{Async, Poll, Sink, StartSend, Stream};
    use std::fmt::Display;

    #[derive(Debug)]
    #[must_use = "streams do nothing unless polled"]
    pub struct Ctx<S, M> {
        stream: S,
        m: M,
    }

    pub fn new<S, M>(stream: S, message: M) -> Ctx<S, M>
    where
        S: Stream,
        M: Display + Send + Sync + 'static,
    {
        Ctx { stream, m: message }
    }

    // Forwarding impl of Sink from the underlying stream
    impl<S, M> Sink for Ctx<S, M>
    where
        S: Sink,
    {
        type SinkItem = S::SinkItem;
        type SinkError = S::SinkError;

        fn start_send(&mut self, item: S::SinkItem) -> StartSend<S::SinkItem, S::SinkError> {
            self.stream.start_send(item)
        }

        fn poll_complete(&mut self) -> Poll<(), S::SinkError> {
            self.stream.poll_complete()
        }

        fn close(&mut self) -> Poll<(), S::SinkError> {
            self.stream.close()
        }
    }

    impl<S, M> Stream for Ctx<S, M>
    where
        S: Stream,
        S::Error: Fail,
        M: Display + Send + Sync + Clone + 'static,
    {
        type Item = S::Item;
        type Error = Error;

        fn poll(&mut self) -> Poll<Option<S::Item>, Error> {
            match self.stream.poll() {
                Ok(Async::Ready(x)) => Ok(Async::Ready(x)),
                Ok(Async::NotReady) => Ok(Async::NotReady),
                Err(e) => Err(e.context(self.m.clone()).into()),
            }
        }
    }

    pub trait StreamExt: Stream {
        /// Wraps the error type in a context type.
        /// The context is coerced into an `Error`.
        fn context<M>(self, m: M) -> Ctx<Self, M>
        where
            M: Display + Send + Sync + 'static,
            Self: Sized,
            Self::Error: Fail,
        {
            new(self, m)
        }
    }

    impl<I: Stream> StreamExt for I {}

    #[cfg(test)]
    mod tests {
        use super::*;
        use futures::stream::once;
        use std::io::{Error, ErrorKind};

        #[test]
        fn context_works_with_streams() {
            let e: Result<String, _> = Err(Error::new(ErrorKind::Other, "oh no!"));
            let mut s = once(e).context("in test");
            let result = s.poll().unwrap_err();

            let xs: Vec<String> = result.iter_chain().map(|x| format!("{}", x)).collect();

            assert_eq!(xs, vec!["in test", "oh no!"]);
        }
    }
}

pub mod future_failure {
    use failure::{Error, Fail};
    use futures::future::Future;
    use futures::{Async, Poll};
    use std::fmt::Display;

    pub struct Ctx<A, M>
    where
        A: Future,
        A::Error: Fail,
    {
        future: A,
        m: Option<M>,
    }

    pub fn new<A, M>(future: A, message: M) -> Ctx<A, M>
    where
        A: Future,
        A::Error: Fail,
    {
        Ctx {
            future,
            m: Some(message),
        }
    }

    impl<A, M> Future for Ctx<A, M>
    where
        A: Future,
        M: Display + Send + Sync + 'static,
        A::Error: Fail,
    {
        type Item = A::Item;
        type Error = Error;

        fn poll(&mut self) -> Poll<A::Item, Error> {
            let e = match self.future.poll() {
                Ok(Async::NotReady) => return Ok(Async::NotReady),
                other => other,
            };
            e.map_err(|err| {
                let message = self.m.take().expect("cannot poll Ctx twice");

                err.context(message).into()
            })
        }
    }

    pub trait FutureExt: Future {
        /// Wraps the error type in a context type.
        /// The context is coerced into an `Error`.
        fn context<M>(self, m: M) -> Ctx<Self, M>
        where
            M: Display + Send + Sync + 'static,
            Self: Sized,
            Self::Error: Fail,
        {
            new(self, m)
        }
    }

    impl<I: Future> FutureExt for I {}

    #[cfg(test)]
    mod tests {
        use super::*;
        use futures::future::err;
        use std::io::{Error, ErrorKind};

        #[test]
        fn context_works_with_futures() {
            let e = Error::new(ErrorKind::Other, "oh no!");

            let mut f = err(e).map(|x: String| x).context("in test");
            let result = f.poll().unwrap_err();

            let xs: Vec<String> = result.iter_chain().map(|x| format!("{}", x)).collect();

            assert_eq!(xs, vec!["in test", "oh no!"]);
        }
    }
}

/// Prints the chain of causes provided
/// by `failure`
pub fn print_cause_chain(e: &Error) {
    for cause in e.iter_chain() {
        eprintln!("{}", cause);
    }
}

pub use future_failure::FutureExt;
pub use stream_failure::StreamExt;
