// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::font_awesome_outline, extensions::NodeExt, generated::css_classes::C};
use seed::{prelude::*, *};

#[derive(Clone, Copy, Debug)]
pub enum Msg {
    Close,
}

pub enum Model {
    Success(String),
    Warn(String),
    Error(String),
}

pub fn view(model: &Model) -> Node<Msg> {
    let (toast_bg, toast_status_bg, icon, status_txt, x) = match model {
        Model::Success(x) => (C.bg_green_600, C.bg_green_500, "check-circle", "Success", x),
        Model::Warn(x) => (C.bg_yellow_600, C.bg_yellow_500, "bell", "Warning", x),
        Model::Error(x) => (C.bg_red_600, C.bg_red_500, "bell", "Error", x),
    };

    div![
        class![
            C.text_white,
            C.fade_in,
            C.p_2,
            toast_bg,
            C.items_center,
            C.leading_none,
            C.rounded_full,
            C.flex,
            C.inline_flex,
        ],
        span![
            class![
                C.flex,
                C.items_center,
                C.rounded_full,
                toast_status_bg,
                C.px_2,
                C.py_1,
                C.text_xs,
                C.font_bold,
                C.mr_3,
            ],
            font_awesome_outline(class![C.h_4, C.w_4, C.mr_1, C.inline], icon),
            status_txt,
        ],
        span![class![C.font_semibold, C.mr_2, C.text_left, C.flex_auto], x],
        font_awesome_outline(class![C.h_4, C.w_4, C.ml_1, C.inline, C.cursor_pointer], "times-circle")
            .with_listener(simple_ev(Ev::Click, Msg::Close))
    ]
}
