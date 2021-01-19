// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future, lock::Mutex, stream, Future, Stream, StreamExt, TryFutureExt, TryStreamExt};
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
        self.0.try_lock().and_then(|mut x| x.take());
    }
    /// Wraps a `Stream` so it will trigger on error.
    pub fn wrap<T, E>(
        &self,
        s: impl Stream<Item = Result<T, E>>,
    ) -> impl Stream<Item = Result<T, E>> {
        s.map_err(self.trigger_fn())
    }
    /// Wraps a `Future` so it will trigger on error.
    pub fn wrap_fut<T, E>(
        &self,
        s: impl Future<Output = Result<T, E>>,
    ) -> impl Future<Output = Result<T, E>> {
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

pub fn when_finished(valve: &Valve) -> impl Future<Output = ()> {
    valve
        .wrap(stream::pending())
        .for_each(|_: ()| future::ready(()))
}

pub fn shared_shutdown() -> (SharedTrigger, Valve) {
    let (exit, valve) = Valve::new();
    let exit = SharedTrigger::new(exit);
    (exit, valve)
}

#[cfg(test)]
mod tests {
    use crate::shared_shutdown;
    use futures::{stream, TryStreamExt};
    use tokio_test::{assert_pending, assert_ready_eq, task::spawn};

    #[test]
    fn test_shared_shutdown() {
        let (mut exit, valve) = shared_shutdown();

        let mut task = spawn(
            valve
                .wrap(stream::pending::<Result<(), ()>>())
                .try_collect::<Vec<_>>(),
        );

        assert_pending!(task.poll());

        exit.trigger();

        assert_ready_eq!(task.poll(), Ok(vec![]));
    }
}
