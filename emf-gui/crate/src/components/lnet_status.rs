// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{attrs, font_awesome, lock_indicator},
    extensions::MergeAttrs,
    generated::css_classes::C,
};
use emf_wire_types::{db::LnetConfigurationRecord, warp_drive::Locks};
use seed::{prelude::*, *};

pub fn network<T>(color: impl Into<Option<&'static str>>) -> Node<T> {
    if let Some(color) = color.into() {
        font_awesome(class![C.w_4, C.h_4, C.inline, C.mr_1, color], "network-wired")
    } else {
        empty![]
    }
}

pub fn view<T>(x: &LnetConfigurationRecord, all_locks: &Locks) -> Node<T> {
    let state = match x.state.as_str() {
        "lnet_up" => span![network(C.text_green_500), "Up"],
        "lnet_down" => span![network(C.text_red_500), "Down"],
        "lnet_unloaded" => span![network(C.text_yellow_500), "Unloaded"],
        "configured" => span![network(C.text_blue_500), "Configured"],
        "unconfigured" => span![network(None), "Unconfigured"],
        "undeployed" => span![network(None), "Undeployed"],
        _ => span![network(C.text_yellow_500), "Unknown"],
    };

    span![
        attrs::container(),
        state,
        lock_indicator::view(all_locks, x).merge_attrs(class![C.ml_2])
    ]
}
