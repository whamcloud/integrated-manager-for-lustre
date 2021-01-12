// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod expansions;
pub mod ss200nv;
pub mod ss9012;

use crate::{
    components::{
        attrs,
        sfa_overview::{sfa_status_border_color, sfa_status_text_color, status_icon, ToHealthState},
        tooltip, Placement,
    },
    extensions::MergeAttrs,
    generated::css_classes::C,
};
use emf_wire_types::sfa::SfaDiskDrive;
use seed::{prelude::*, *};
use std::{collections::BTreeSet, iter, sync::Arc};

pub(crate) fn failed_drives<T>(slots: BTreeSet<i32>) -> Node<T> {
    let txt = match slots.len() {
        0 => return div![],
        1 => "slot ",
        _ => "slots ",
    };

    let slots: Vec<_> = slots.into_iter().map(|x| x.to_string()).collect();

    div![
        class![C.flex, C.items_center],
        circle().merge_attrs(class![C.text_red_600, C.self_center, C.mr_2, C.w_3, C.h_3]),
        "Failed drive in ",
        span![class![C.text_red_500, C.pl_1], txt, slots.join(", ")]
    ]
}

pub(crate) fn circle<T>() -> Node<T> {
    svg![
        class![C.stroke_current, C.inline, C.justify_self_center],
        attrs! {
          At::ViewBox => "0 0 10 10"
        },
        circle![attrs! {
          At::R => "4",
          At::Cx => percent(50),
          At::Cy => percent(50),
          At::StrokeWidth => 1.2,
          At::Fill => "transparent",
        }],
    ]
}

pub(crate) fn disk<T>(slot: i32, x: &Option<Arc<SfaDiskDrive>>) -> Node<T> {
    let (circle_color, bg_color, border_color) = if let Some(x) = x {
        let (circle_color, border_color) = if x.failed {
            (C.text_red_500, C.border_red_500)
        } else {
            (C.text_green_500, C.border_gray_300)
        };

        (circle_color, C.bg_white, border_color)
    } else {
        (C.text_gray_500, C.bg_gray_400, C.border_gray_300)
    };

    div![
        attrs::container(),
        class![
            bg_color,
            border_color,
            C.border_3,
            C.content_center,
            C.grid_rows_2,
            C.grid,
            C.rounded_md,
            circle_color,
        ],
        tooltip::view(&format!("Slot {}", slot), Placement::Top),
        circle().merge_attrs(class![C.mt_1, C.w_2of3]),
        div![
            class![C.grid, C.grid_rows_6],
            iter::repeat(hr![class![C.border, border_color, C.justify_self_center, C.w_1of2]])
                .take(6)
                .collect::<Vec<_>>()
        ],
    ]
}

pub(crate) fn sfa_item<T>(x: impl ToHealthState, children: impl View<T>) -> Node<T> {
    let health_state = x.to_health_state();

    div![
        class![C.border_2, C.border_gray_200],
        attrs::container(),
        tooltip::view(&x.to_health_state_reason(), Placement::Top),
        div![
            class![
                C.bg_white,
                C.border_4,
                C.flex_col,
                C.flex,
                C.h_full,
                C.items_center,
                C.justify_center,
                C.rounded_md,
            ],
            class![sfa_status_border_color(&health_state)],
            status_icon(&health_state).merge_attrs(class![C.w_6, C.h_6, C.my_1, sfa_status_text_color(&health_state)]),
            children.els(),
        ],
    ]
}
