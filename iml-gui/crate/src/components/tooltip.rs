// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{arrow, Placement},
    extensions::MergeAttrs,
    generated::css_classes::C,
};
use seed::{prelude::*, *};

/// Render a tooltip with vaild CSS color string.
pub(crate) fn base_color_view<T>(content: &str, placement: Placement, color: &str) -> Node<T> {
    let tooltip_top_styles = style! {
        St::Transform => "translate(50%, -100%)",
        St::Top => 0,
        St::Right => percent(50),
        St::MarginTop => px(-3),
    };

    let tooltip_right_styles = style! {
        St::Transform => "translateY(50%)",
        St::Left => percent(100),
        St::Bottom => percent(50),
        St::MarginLeft => px(8),
    };

    let tooltip_bottom_styles = style! {
        St::Transform => "translateX(50%)",
        St::Top => percent(100),
        St::Right => percent(50),
        St::MarginTop => px(3),
        St::PaddingTop => px(5)
    };

    let tooltip_left_styles = style! {
        St::Transform => "translate(calc(-100% - 8px),50%)",
        St::Bottom => percent(50),
    };

    let tooltip_style = match placement {
        Placement::Left => tooltip_left_styles,
        Placement::Right => tooltip_right_styles,
        Placement::Top => tooltip_top_styles,
        Placement::Bottom => tooltip_bottom_styles,
    };

    div![
        class![C.absolute, C.pointer_events_none, C.z_20, C.whitespace_normal],
        style! {
            St::WillChange => "transform"
        },
        tooltip_style,
        arrow(placement, color),
        div![
            class![
                C.text_center,
                C.text_white,
                C.text_sm,
                C.py_1,
                C.px_3,
                C.rounded,
                C.opacity_90,
            ],
            style! {
                St::Width => px(250),
                St::BackgroundColor => color,
            },
            El::from_html(content)
        ]
    ]
}

pub(crate) fn color_view<T>(content: &str, placement: Placement, color: &str) -> Node<T> {
    base_color_view(content, placement, color).merge_attrs(class![C.hidden, C.group_hover__block,])
}

/// Render a hover tooltip.
pub(crate) fn view<T>(content: &str, direction: Placement) -> Node<T> {
    color_view(content, direction, "black")
}

/// Render a tooltip with a red error color.
pub(crate) fn base_error_view<T>(content: &str, direction: Placement) -> Node<T> {
    base_color_view(content, direction, "red")
}
