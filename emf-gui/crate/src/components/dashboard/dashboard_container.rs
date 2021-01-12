// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{prelude::*, *};

pub fn view<T>(title: &str, chart: impl View<T>) -> Node<T> {
    div![
        class![C.flex, C.flex_col, C.bg_white, C.rounded_lg],
        div![
            class![C.px_6, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], title]
        ],
        chart.els(),
    ]
}
