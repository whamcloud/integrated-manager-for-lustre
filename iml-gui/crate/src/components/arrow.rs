// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::Placement, generated::css_classes::C};
use seed::{prelude::*, *};

pub(crate) fn arrow<T>(direction: Placement, color: &str) -> Node<T> {
    let arrow_top_styles = style! {
        St::Top => percent(100),
        St::Left => percent(50),
        St::MarginLeft => px(-5),
        St::BorderWidth => "5px 5px 0",
        St::BorderTopColor => color
    };

    let arrow_right_styles = style! {
        St::Top => percent(50),
        St::Right => percent(100),
        St::MarginTop => px(-5),
        St::BorderWidth => "5px 5px 5px 0",
        St::BorderRightColor => color
    };

    let arrow_bottom_styles = style! {
        St::Top => 0,
        St::Left => percent(50),
        St::MarginLeft => px(-5),
        St::BorderWidth => "0 5px 5px",
        St::BorderBottomColor => color
    };

    let arrow_left_styles = style! {
        St::Top => percent(50),
        St::Left => percent(100),
        St::MarginTop => px(-5),
        St::BorderWidth => "5px 0 5px 5px",
        St::BorderLeftColor => color
    };

    let arrow_style = match direction {
        Placement::Left => arrow_left_styles,
        Placement::Right => arrow_right_styles,
        Placement::Top => arrow_top_styles,
        Placement::Bottom => arrow_bottom_styles,
    };

    div![
        class![C.w_0, C.h_0, C.border_solid, C.border_transparent, C.absolute],
        arrow_style,
    ]
}
