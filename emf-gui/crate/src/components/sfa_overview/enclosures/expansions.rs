// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::sfa_overview::{enclosures::sfa_item, Expansion},
    generated::css_classes::C,
    route::Route,
};
use seed::{prelude::*, *};
use std::ops::Deref;

fn expansion_item<T>(x: Option<&Expansion>) -> Node<T> {
    match x {
        Some(Expansion::SS9012(m)) => sfa_item(
            m.enclosure.deref(),
            a![
                class![C.text_blue_500, C.hover__underline],
                attrs! {
                    At::Href => Route::SfaEnclosure(m.enclosure.id.into()).to_href()
                },
                m.enclosure.model
            ],
        ),
        None => div![
            class![C.border_2, C.border_gray_200],
            div![class![
                C.bg_gray_300,
                C.border_4,
                C.border_gray_400,
                C.flex_col,
                C.flex,
                C.h_full,
                C.items_center,
                C.justify_center,
                C.rounded_md,
            ]]
        ],
    }
}

pub(crate) fn view<T>(platform: &str, expansions: &[Expansion]) -> Node<T> {
    match platform {
        "SFA200NVXE" | "SFA200NVE" => {
            // 0 expansions
            empty![]
        }
        "SFA400NVXE" | "SFA400NVE" => {
            // 4 expansions

            div![
                class![C.row_span_2, C.grid, C.grid_cols_4, C.bg_gray_300, C.rounded, C.p_1],
                (0..=3).map(|idx| expansions.get(idx)).map(expansion_item)
            ]
        }
        "SFA7990E" | "SFA7990XE" => {
            // 4 expansions
            empty![]
        }
        "SFA14KXE" => {
            // 20 expansions
            empty![]
        }
        "SFA18KE" | "SFA18KXE" => {
            // 20 Expansions
            empty![]
        }
        _ => empty![],
    }
}
