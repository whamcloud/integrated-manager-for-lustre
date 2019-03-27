// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{task, Async, Future, Poll};
use seed::prelude::{Closure, JsValue};
use std::{cell::RefCell, rc::Rc};
use wasm_bindgen::JsCast;

pub struct Sleep {
    millis: i32,
    closure: Option<Closure<dyn FnMut()>>,
    token: Option<i32>,
    fired: Rc<RefCell<Option<bool>>>,
}

impl Sleep {
    pub fn new(millis: i32) -> Self {
        Sleep {
            millis,
            closure: None,
            token: None,
            fired: Rc::new(RefCell::new(Some(false))),
        }
    }
    fn run(&mut self, task: task::Task) {
        let fired = self.fired.clone();

        // Construct a new closure.
        let closure = Closure::wrap(Box::new(move || {
            fired
                .try_borrow_mut()
                .expect("Failed to borrow mutable fired")
                .take();
            task.notify();
        }) as Box<dyn FnMut()>);

        let window = web_sys::window().expect("Could not obtain window ref");

        let token = window
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
            let window = web_sys::window().expect("Could not obtain window ref");
            window.clear_timeout_with_handle(t);
        }
    }
}

impl Future for Sleep {
    type Item = ();
    type Error = JsValue;
    fn poll(&mut self) -> Poll<(), JsValue> {
        if self.token.is_none() {
            self.run(task::current());
        }

        let fired = self
            .fired
            .try_borrow()
            .expect("Failed borrowing from fired")
            .is_none();

        if fired {
            Ok(Async::Ready(()))
        } else {
            Ok(Async::NotReady)
        }
    }
}
