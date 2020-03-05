// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome_outline, modal, stratagem::scan_stratagem_modal},
    extensions::MergeAttrs,
    generated::css_classes::C,
    GMsg,
};
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub disabled: bool,
    pub locked: bool,
    pub fs_id: u32,
    pub scan_stratagem_modal: scan_stratagem_modal::Model,
}

impl Model {
    pub fn new(fs_id: u32) -> Self {
        Self {
            fs_id,
            scan_stratagem_modal: scan_stratagem_modal::Model::new(fs_id),
            ..Default::default()
        }
    }
}

#[derive(Clone)]
pub enum Msg {
    ScanStratagemModal(Box<scan_stratagem_modal::Msg>),
    ShowModal,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ScanStratagemModal(msg) => {
            log!("Got scan staragem modal message");
            scan_stratagem_modal::update(
                *msg,
                &mut model.scan_stratagem_modal,
                &mut orders.proxy(|x| Msg::ScanStratagemModal(Box::new(x))),
            );
        }
        Msg::ShowModal => scan_stratagem_modal::update(
            scan_stratagem_modal::Msg::Modal(modal::Msg::Open),
            &mut model.scan_stratagem_modal,
            &mut orders.proxy(|_| Msg::ShowModal),
        ),
    }
}

pub fn view(model: &Model) -> Vec<Node<Msg>> {
    let mut scan_stratagem_button = button![
        class![
            C.bg_blue_500,
            C.hover__bg_blue_700,
            C.text_white,
            C.mt_24,
            C.font_bold,
            C.py_2,
            C.px_2,
            C.rounded,
            C.w_full,
            C.text_sm
        ],
        "Scan Filesystem Now",
        font_awesome_outline(class![C.inline, C.h_4, C.w_4], "")
    ];

    if !model.disabled && !model.locked && !model.scan_stratagem_modal.scanning {
        scan_stratagem_button.add_listener(ev(Ev::Click, |_| Msg::ShowModal));
    } else {
        scan_stratagem_button = scan_stratagem_button
            .merge_attrs(attrs! {At::Disabled => "disabled"})
            .merge_attrs(class![C.cursor_not_allowed, C.opacity_50]);
    }

    vec![
        scan_stratagem_button,
        scan_stratagem_modal::view(&model.scan_stratagem_modal).map_msg(|x| Msg::ScanStratagemModal(Box::new(x))),
    ]
}
