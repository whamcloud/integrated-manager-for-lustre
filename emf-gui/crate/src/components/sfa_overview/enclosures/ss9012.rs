// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::sfa_overview::enclosures::{disk, failed_drives, sfa_item},
    extensions::MergeAttrs as _,
    generated::css_classes::C,
};
use emf_wire_types::sfa::{SfaDiskDrive, SfaEnclosure, SfaPowerSupply};
use seed::{prelude::*, *};
use std::{
    collections::{BTreeSet, HashMap},
    sync::Arc,
};

#[derive(Debug, PartialEq, Eq)]
pub(crate) struct Model {
    pub(crate) enclosure: Arc<SfaEnclosure>,
    pub(crate) disks: HashMap<i32, Arc<SfaDiskDrive>>,
    pub(crate) psu1: Option<Arc<SfaPowerSupply>>,
    pub(crate) psu2: Option<Arc<SfaPowerSupply>>,
    pub(crate) psu3: Option<Arc<SfaPowerSupply>>,
    pub(crate) psu4: Option<Arc<SfaPowerSupply>>,
    pub(crate) psu5: Option<Arc<SfaPowerSupply>>,
    pub(crate) psu6: Option<Arc<SfaPowerSupply>>,
}

pub(crate) fn view<T>(x: &Model) -> Node<T> {
    let failed_slots: BTreeSet<_> = x
        .disks
        .iter()
        .filter(|(_, disk)| disk.failed)
        .map(|(slot, _)| slot)
        .copied()
        .collect();

    let slots: Vec<_> = (1..=90).map(|idx| (idx, x.disks.get(&idx).map(Arc::clone))).collect();
    let slots: Vec<_> = slots.chunks(5).collect();

    div![
        class![C.bg_white, C.grid],
        div![
            class![C.px_6, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], x.enclosure.model]
        ],
        div![
            class![C.grid, C.inline_block, C.p_4],
            style! { St::JustifySelf => "center"},
            div![
                class![C.bg_gray_300, C.grid_flow_col, C.grid, C.rounded, C.col_span_6, C.p_1],
                sfa_item(x.psu1.as_deref(), span!["PSU1"]).merge_attrs(class![C.w_20]),
                sfa_item(x.psu2.as_deref(), span!["PSU2"]).merge_attrs(class![C.w_20]),
                sfa_item(x.psu5.as_deref(), span!["REG1"]).merge_attrs(class![C.w_20]),
                sfa_item(x.psu6.as_deref(), span!["REG2"]).merge_attrs(class![C.w_20]),
                sfa_item(x.psu3.as_deref(), span!["PSU3"]).merge_attrs(class![C.w_20]),
                sfa_item(x.psu4.as_deref(), span!["PSU4"]).merge_attrs(class![C.w_20]),
            ],
            div![
                class![C.bg_gray_300, C.col_span_6, C.grid_flow_col, C.grid, C.h_12, C.p_1],
                div![
                    class![C.border_2, C.border_gray_200],
                    div![
                        class![
                            C.bg_gray_300,
                            C.border_4,
                            C.border_gray_400,
                            C.flex_col,
                            C.flex,
                            C.h_full,
                            C.items_center,
                            C.justify_center,
                            C.rounded_md,
                        ],
                        "ESM A"
                    ]
                ],
                div![
                    class![C.border_2, C.border_gray_200],
                    div![
                        class![
                            C.bg_gray_300,
                            C.border_4,
                            C.border_gray_400,
                            C.flex_col,
                            C.flex,
                            C.h_full,
                            C.items_center,
                            C.justify_center,
                            C.rounded_md,
                        ],
                        "ESM B"
                    ]
                ],
            ]
        ],
        div![
            class![C.grid, C.inline_block, C.p_4],
            style! { St::JustifySelf => "center"},
            failed_drives(failed_slots).merge_attrs(class![C.row_span_2, C.ml_3]),
            div![
                class![C.grid],
                class![
                    C.bg_gray_200,
                    C.border_2,
                    C.gap_2,
                    C.grid,
                    C.p_1
                    C.rounded,
                    C.row_span_6,
                ],
                style! { St::GridTemplateColumns => "repeat(3, min-content)" },
                slots.chunks(3).rev().flatten().map(|x| disk_section(x))
            ]
        ]
    ]
}

fn disk_section<T>(disks: &[(i32, Option<Arc<SfaDiskDrive>>)]) -> Node<T> {
    div![
        class![C.grid, C.gap_1, C.h_20],
        style! { St::GridTemplateColumns => "repeat(5, min-content)" },
        disks.iter().map(|(idx, x)| disk(*idx, x).merge_attrs(class![C.w_6]))
    ]
}
