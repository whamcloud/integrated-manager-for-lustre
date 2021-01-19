// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{prelude::*, *};

/// A loading interstitial. Needs to be kept in sync with
/// emf-gui/entries/templates/loading_page.hbs
/// to ensure a consistent loading experience.
pub fn view<T>() -> Node<T> {
    div![
        class![
            C.h_screen,
            C.flex,
            C.flex_col,
            C.items_center,
            C.justify_center,
            C.text_gray_500
        ],
        svg![
            class![
                C.fill_current,
                C.mt_4,
                C.h_12,
                C.rotate,
                C.sm__mt_5,
                C.sm__h_16,
                C.lg__mt_8,
                C.lg__h_24
            ],
            attrs! {
                At::ViewBox => "0 0 100 100",
                At::PreserveAspectRatio => "xMidYMid",
                At::Style => "background: rgba(0, 0, 0, 0) none repeat scroll 0% 0%;"
            },
            path![attrs! {
                At::Stroke => "none",
                At::D => "M10 50A40 40 0 0 0 90 50A40 42 0 0 1 10 50"
            }],
        ]
    ]
}
