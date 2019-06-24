// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{
    events::{mouse_ev, Ev},
    attrs, button, class, div,
    dom_types::{At, El, UpdateEl},
    i, li,
    prelude::IndexMap,
    style, ul,
};

#[derive(Clone)]
pub enum Msg {
    Open(bool),
}

pub enum State {
    Populated(bool, Vec<El<Msg>>),
    Disabled,
    Empty,
    Waiting,
}

pub fn dropdown_header<T>(label: &str) -> El<T> {
    li![
        class!["dropdown-header"],
        style! {"user-select" => "none"},
        label
    ]
}

pub fn action_dropdown(state: State) -> El<Msg> {
    const BTN_CLASSES: &str = "btn btn-primary btn-sm dropdown-toggle";

    let disabled_attrs = attrs! {At::Disabled => true; At::Class => BTN_CLASSES};

    let open_class = if let State::Populated(true, _) = state {
        "open"
    } else {
        ""
    };

    let els = match state {
        State::Empty => vec![button![&disabled_attrs, "No Actions"]],
        State::Disabled => vec![button![&disabled_attrs, "Disabled"]],
        State::Waiting => vec![button![
            &disabled_attrs,
            "Waiting",
            i![class!["fa", "fa-spinner", "fa-spin"]]
        ]],
        State::Populated(is_open, lis) => vec![
            button![
                attrs! {At::Class => BTN_CLASSES},
                mouse_ev(Ev::Click, move |ev| {
                    ev.stop_propagation();
                    ev.prevent_default();
                    Msg::Open(!is_open)
                }),
                "Actions",
                i![class!["fa", "fa-caret-down", "icon-caret-down"]]
            ],
            ul![class!["dropdown-menu", &open_class], lis],
        ],
    };

    div![
        class!["action-dropdown"],
        div![class!["btn-group dropdown", &open_class], els]
    ]
}
