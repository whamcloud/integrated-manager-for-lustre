// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{class, div, prelude::*, *};

pub fn datepicker<T>() -> Node<T> {
    div![
        class![C.text_center],
        div![
            class![C.inline_block, C.rounded_full, C.px_2, C.text_gray_400, C.text_xs,],
            button![
                class![C.inline_block, C.bg_blue_500, C.px_6, C.rounded_l_full, C.text_white,],
                "Day",
            ],
            button![
                class![
                    C.inline_block,
                    C.bg_gray_200,
                    C.px_6,
                    C.border_l,
                    C.border_r,
                    C.border_white,
                    C.border_l_2,
                    C.border_r_2,
                ],
                "2 Days",
            ],
            button![class![C.inline_block, C.px_6, C.bg_gray_200, C.rounded_r_full,], "Week",],
        ],
    ]
}
