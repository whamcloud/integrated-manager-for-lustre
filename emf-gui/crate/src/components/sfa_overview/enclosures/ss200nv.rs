// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::sfa_overview::enclosures::{disk, failed_drives, sfa_item},
    extensions::MergeAttrs as _,
    generated::css_classes::C,
};
use emf_wire_types::sfa::{SfaController, SfaDiskDrive, SfaEnclosure, SfaPowerSupply};
use seed::{prelude::*, *};
use std::{
    collections::{BTreeSet, HashMap},
    ops::Deref,
    sync::Arc,
};

#[derive(Debug, PartialEq, Eq)]
pub(crate) struct Model {
    pub(crate) enclosure: Arc<SfaEnclosure>,
    pub(crate) disks: HashMap<i32, Arc<SfaDiskDrive>>,
    pub(crate) top_controller: Option<Arc<SfaController>>,
    pub(crate) bottom_controller: Option<Arc<SfaController>>,
    pub(crate) psu1: Option<Arc<SfaPowerSupply>>,
    pub(crate) psu2: Option<Arc<SfaPowerSupply>>,
}

pub(crate) fn drives<T>(x: &Model, cramped: bool) -> Node<T> {
    let failed_slots: BTreeSet<_> = x
        .disks
        .iter()
        .filter(|(_, disk)| disk.failed)
        .map(|(slot, _)| slot)
        .copied()
        .collect();

    let slots: Vec<_> = (1..=24).map(|idx| (idx, x.disks.get(&idx).map(Arc::clone))).collect();
    let slots: Vec<_> = slots.chunks(8).collect();

    div![
        class![C.grid],
        failed_drives(failed_slots).merge_attrs(class![C.row_span_2, C.ml_3]),
        if cramped {
            div![
                class![C.bg_gray_200, C.border_2, C.p_1, C.rounded, C.row_span_6],
                sfa_item(x.enclosure.deref(), span![x.enclosure.model]).merge_attrs(class![C.bg_gray_300, C.h_full]),
            ]
        } else {
            div![
                class![
                    C.bg_gray_200,
                    C.border_2,
                    C.gap_2,
                    C.grid_cols_3,
                    C.grid,
                    C.p_1,
                    C.rounded,
                    C.row_span_6
                ],
                slots.into_iter().map(disk_section)
            ]
        }
    ]
}

pub(crate) fn view<T>(x: &Model, cramped: bool) -> Node<T> {
    div![
        class![C.grid, C.gap_4, C.min_h_80, C.w_full],
        style! {
            St::GridTemplateRows => "minmax(200px, 0.7fr) minmax(0, 1fr)"
        },
        drives(&x, cramped),
        div![
            class![C.grid, C.gap_2],
            div![
                class![C.bg_gray_300, C.grid_flow_col, C.grid, C.rounded, C.row_span_6, C.p_1],
                sfa_item(x.psu1.as_deref(), span!["PSU1"]).merge_attrs(class![C.col_span_1]),
                div![
                    class![C.col_span_10, C.grid],
                    sfa_item(x.top_controller.as_deref(), span!["UPPER"]),
                    sfa_item(x.bottom_controller.as_deref(), span!["LOWER"]),
                ],
                sfa_item(x.psu2.as_deref(), span!["PSU2"]).merge_attrs(class![C.col_span_1]),
            ]
        ]
    ]
}

fn disk_section<T>(disks: &[(i32, Option<Arc<SfaDiskDrive>>)]) -> Node<T> {
    div![
        class![C.grid, C.grid_cols_8, C.gap_1],
        disks.iter().map(|(idx, x)| disk(*idx, x))
    ]
}
