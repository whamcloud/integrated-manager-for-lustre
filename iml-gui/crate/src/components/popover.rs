// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{arrow, Placement},
    generated::css_classes::C,
};
use seed::{prelude::*, *};

pub fn title_view<T>(content: &str) -> Node<T> {
    div![
        class![C.bg_gray_200, C.py_1, C.px_3],
        h4![class![C.font_normal], content]
    ]
}

pub fn content_view<T>(content: impl View<T>) -> Node<T> {
    div![class![C.py_2, C.px_3, C.text_sm], content.els()]
}

pub fn view<T>(content: impl View<T>, placement: Placement) -> Node<T> {
    let color = "#e2e8f0";

    let popover_top_styles = style! {
        St::Transform => "translate(50%, -100%)",
        St::Top => 0,
        St::Right => percent(50),
        St::MarginTop => px(-3),
    };

    let popover_right_styles = style! {
        St::Transform => "translateY(50%)",
        St::Left => percent(100),
        St::Bottom => percent(50),
        St::MarginLeft => px(5),
    };

    let popover_bottom_styles = style! {
        St::Transform => "translateX(50%)",
        St::Top => percent(100),
        St::Right => percent(50),
        St::MarginTop => px(3),
        St::PaddingTop => px(5)
    };

    let popover_left_styles = style! {
        St::Transform => "translate(-100%,50%)",
        St::Bottom => percent(50),
        St::MarginRight => px(5),
    };

    let popover_style = match placement {
        Placement::Left => popover_left_styles,
        Placement::Right => popover_right_styles,
        Placement::Top => popover_top_styles,
        Placement::Bottom => popover_bottom_styles,
    };

    div![
        class![
            C.absolute,
            C.pointer_events_none,
            C.z_10,
            C.hidden,
            C.group_focus__block,
        ],
        popover_style,
        arrow(placement, color),
        div![class![C.rounded, C.shadow, C.bg_white, C.text_black], content.els(),]
    ]
}
