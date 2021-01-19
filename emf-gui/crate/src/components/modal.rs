// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::font_awesome, generated::css_classes::C, key_codes, GMsg};
use seed::{prelude::*, *};

#[derive(Default, Debug)]
pub struct Model {
    pub open: bool,
}

type ParentMsg<T> = fn(Msg) -> T;

#[derive(Clone, PartialEq, Debug)]
pub enum Msg {
    KeyDown(u32),
    Close,
    Open,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::KeyDown(code) => {
            if code == key_codes::ESC {
                orders.send_msg(Msg::Close);
            }
        }
        Msg::Close => {
            model.open = false;
        }
        Msg::Open => {
            model.open = true;
        }
    }
}

pub fn title_view<T>(p_msg: ParentMsg<T>, children: impl View<T>) -> Node<T> {
    div![
        class![C.flex, C.justify_between, C.items_center, C.pb_3,],
        p![class![C.text_2xl, C.font_bold,], children.els()],
        div![
            class![C.cursor_pointer, C.z_50,],
            font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "times"),
            ev(Ev::Click, move |_| p_msg(Msg::Close))
        ],
    ]
}

pub fn footer_view<T>(children: impl View<T>) -> Node<T> {
    div![class![C.flex, C.justify_end, C.pt_2,], children.els()]
}

pub fn content_view<T>(p_msg: ParentMsg<T>, children: impl View<T>) -> Node<T> {
    div![
        class![
            C.bg_white,
            C.w_10of12,
            C.md__max_w_3xl,
            C.mx_auto,
            C.rounded,
            C.shadow_lg,
            C.z_50,
        ],
        div![
            class![
                C.absolute,
                C.top_0,
                C.right_0,
                C.cursor_pointer,
                C.flex,
                C.flex_col,
                C.items_center,
                C.mt_4,
                C.mr_4,
                C.text_white,
                C.text_sm,
                C.z_50,
            ],
            ev(Ev::Click, move |_| p_msg(Msg::Close)),
            font_awesome(class![C.w_4, C.h_4, C.inline], "times"),
            span![class![C.text_sm,], "(Esc)",],
        ],
        div![
            class![C.py_4, C.text_left, C.px_6, C.max_h_screen, C.overflow_auto],
            children.els()
        ]
    ]
}

pub fn bg_view<T>(open: bool, p_msg: ParentMsg<T>, children: impl View<T>) -> Node<T> {
    if !open {
        return empty![];
    }

    div![
        class![
            C.fixed,
            C.flex,
            C.h_full,
            C.items_center,
            C.justify_center,
            C.left_0,
            C.top_0,
            C.w_full,
            C.z_50
        ],
        attrs! {At::TabIndex => 0, At::AutoFocus => true},
        keyboard_ev("keydown", move |ev| p_msg(Msg::KeyDown(ev.key_code()))),
        div![
            class![C.absolute, C.w_full, C.h_full],
            style! {St::BackgroundColor => "rgba(26, 32, 44, 0.6)"},
            children.els()
        ],
    ]
}
