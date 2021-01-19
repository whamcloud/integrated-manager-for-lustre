// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{prelude::*, *};

/// Renders a toggle component that is just a
/// styled checkbox element.
pub(crate) fn toggle<T>() -> Node<T> {
    input![
        class![
            C.appearance_none,
            C.bg_gray_200,
            C.border_2,
            C.border_gray_400,
            C.checked__border_green_400
            C.checked__text_green_400,
            C.focus__outline_none,
            C.focus__shadow_outline,
            C.h_5,
            C.p_px,
            C.rounded_28px,
            C.text_gray_500,
            C.toggle,
            C.w_10,
        ],
        attrs! { At::Type => "checkbox"}
    ]
}
