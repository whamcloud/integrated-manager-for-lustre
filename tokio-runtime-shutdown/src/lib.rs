// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;
use futures::Stream;
use parking_lot::Mutex;
use std::sync::Arc;
use stream_cancel::{Trigger, Valve};

/// Wraps a `stream_cancel::Trigger` so it can be shared
/// across tasks.
#[derive(Clone)]
pub struct SharedTrigger(Arc<Mutex<Option<Trigger>>>);

impl SharedTrigger {
    pub fn new(t: Trigger) -> Self {
        Self(Arc::new(Mutex::new(Some(t))))
    }
    /// Triggers the exit. This will halt all
    /// associated tasks that have been wrapped.
    pub fn trigger(&mut self) {
        self.0.lock().take();
    }
    /// Wraps a `Stream` so it will trigger on error.
    pub fn wrap<T, E>(
        &self,
        s: impl Stream<Item = T, Error = E>,
    ) -> impl Stream<Item = T, Error = E> {
        s.map_err(self.trigger_fn())
    }
    /// Wraps a `Future` so it will trigger on error.
    pub fn wrap_fut<T, E>(
        &self,
        s: impl Future<Item = T, Error = E>,
    ) -> impl Future<Item = T, Error = E> {
        s.map_err(self.trigger_fn())
    }
    pub fn trigger_fn<E>(&self) -> impl FnMut(E) -> E {
        let mut cloned = self.clone();

        move |e| {
            cloned.trigger();

            e
        }
    }
}

pub fn shared_shutdown() -> (SharedTrigger, Valve) {
    let (exit, valve) = Valve::new();
    let exit = SharedTrigger::new(exit);
    (exit, valve)
}

#[cfg(test)]
mod tests {
    use crate::shared_shutdown;
    use tokio::prelude::*;

    #[test]
    fn test_shared_shutdown() {
        let (exit, valve) = shared_shutdown();
        let listener1 = tokio::net::TcpListener::bind(&"0.0.0.0:0".parse().unwrap()).unwrap();
        let s = stream::iter_result(vec![Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "boom",
        ))]);
        let incoming1 = valve.wrap(listener1.incoming());
        let incoming2 = exit.wrap(valve.wrap(s));

        let mut rt = tokio::runtime::Runtime::new().unwrap();
        rt.spawn(
            incoming1
                .map_err(exit.trigger_fn())
                .map_err(|e| eprintln!("{:?}", e))
                .for_each(|sock| {
                    let (reader, writer) = sock.split();
                    tokio::spawn(
                        tokio::io::copy(reader, writer)
                            .map(|amt| println!("wrote {:?} bytes", amt))
                            .map_err(|err| eprintln!("IO error {:?}", err)),
                    )
                }),
        );

        rt.spawn(
            incoming2
                .map_err(|e| eprintln!("{:?}", e))
                .for_each(|_: ()| Ok(())),
        );

        rt.shutdown_on_idle().wait().unwrap();
    }
}
