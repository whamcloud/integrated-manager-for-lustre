// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Msg;
use seed::{attrs, button, class, i, prelude::*};

const BTN_CLASSES: &str = "btn btn-primary btn-sm dropdown-toggle";

pub fn get_button(has_locks: bool, has_actions: bool, waiting: bool, next_open: Msg) -> El<Msg> {
    if has_locks {
        button![
            attrs! {At::Disabled => true; At::Class => BTN_CLASSES},
            "Disabled"
        ]
    } else if waiting {
        button![
            attrs! {At::Class => BTN_CLASSES; At::Disabled => true},
            "Waiting",
            i![class!["fa", "fa-spinner", "fa-spin"]]
        ]
    } else if has_actions {
        button![
            attrs! {At::Class => BTN_CLASSES},
            mouse_ev(Ev::Click, move |ev| {
                ev.stop_propagation();
                ev.prevent_default();
                next_open.clone()
            }),
            "Actions",
            i![class!["fa", "fa-caret-down", "icon-caret-down"]]
        ]
    } else {
        button![
            attrs! {At::Disabled => true; At::Class => BTN_CLASSES},
            "No Actions"
        ]
    }
}
