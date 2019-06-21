// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{task, Async, Future, Poll};
use seed::{prelude::Closure, window};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use wasm_bindgen::JsCast;

pub struct Sleep {
    millis: i32,
    closure: Option<Closure<dyn FnMut()>>,
    token: Option<i32>,
    fired: Arc<AtomicBool>,
}

impl Sleep {
    pub fn new(millis: i32) -> Self {
        Sleep {
            millis,
            closure: None,
            token: None,
            fired: Arc::new(AtomicBool::new(false)),
        }
    }
    fn run(&mut self, task: task::Task) {
        let fired = Arc::clone(&self.fired);

        // Construct a new closure.
        let closure = Closure::wrap(Box::new(move || {
            fired.store(true, Ordering::Relaxed);
            task.notify();
        }) as Box<dyn FnMut()>);

        let token = window()
            .set_timeout_with_callback_and_timeout_and_arguments_0(
                closure.as_ref().unchecked_ref(),
                self.millis,
            )
            .expect("Issue calling set timeout");

        self.token = Some(token);
        self.closure = Some(closure);
    }
}

impl Drop for Sleep {
    fn drop(&mut self) {
        if let Some(t) = self.token {
            window().clear_timeout_with_handle(t);
        }
    }
}

impl Future for Sleep {
    type Item = ();
    type Error = ();
    fn poll(&mut self) -> Poll<(), ()> {
        if self.token.is_none() {
            self.run(task::current());
        }

        let fired = self.fired.load(Ordering::Relaxed);

        if fired {
            Ok(Async::Ready(()))
        } else {
            Ok(Async::NotReady)
        }
    }
}
