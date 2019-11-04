// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{
    attrs, button, class, div,
    dom_types::{At, El, UpdateEl},
    i, li,
    prelude::*,
    style, ul,
};

pub fn dropdown_header<T>(label: &str) -> Node<T> {
    li![
        class!["dropdown-header"],
        style! {"user-select" => "none"},
        label
    ]
}

pub fn dropdown<T>(
    btn_classes: &[&'static str],
    btn_name: &str,
    open: bool,
    children: Vec<Node<T>>,
) -> Node<T> {
    let open_class = if open { "open" } else { "" };

    let mut btn: Node<_> = button![
        class!["btn", "dropdown-toggle"],
        btn_name,
        i![class!["fa", "fa-fw", "fa-caret-down", "icon-caret-down"]]
    ];

    for &c in btn_classes {
        btn.add_class(c);
    }

    div![
        class!["btn-group", "dropdown", open_class],
        btn,
        ul![class!["dropdown-menu", &open_class], children],
    ]
}

pub fn action_dropdown<T>(open: bool, is_locked: bool, children: Vec<Node<T>>) -> Node<T> {
    let btn_classes = "btn btn-primary btn-sm";

    let el = if is_locked {
        button![
            attrs! {At::Disabled => true, At::Class => btn_classes },
            "Disabled"
        ]
    } else if children.is_empty() {
        button![
            attrs! {At::Disabled => true, At::Class => btn_classes },
            "No Actions"
        ]
    } else {
        dropdown(&[btn_classes], "Actions", open, children)
    };

    div![class!["action-dropdown"], el]
}
