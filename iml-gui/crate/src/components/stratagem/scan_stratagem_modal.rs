// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        command_modal, font_awesome, modal,
        stratagem::{duration_picker, validation},
    },
    extensions::{MergeAttrs as _, NodeExt as _},
    generated::css_classes::C,
    key_codes, GMsg, RequestExt,
};
use iml_graphql_queries::{stratagem, Response};
use seed::{prelude::*, *};
use std::{sync::Arc, time::Duration};

#[derive(Default)]
pub struct Model {
    pub modal: modal::Model,
    pub report_duration: duration_picker::Model,
    pub purge_duration: duration_picker::Model,
    pub fsname: String,
    pub scanning: bool,
}

impl Model {
    pub fn new(fsname: String) -> Self {
        Self {
            fsname,
            ..Default::default()
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    ReportDurationPicker(duration_picker::Msg),
    PurgeDurationPicker(duration_picker::Msg),
    SubmitScan,
    Scanned(fetch::ResponseDataResult<Response<stratagem::fast_file_scan::Resp>>),
    Modal(modal::Msg),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ReportDurationPicker(msg) => {
            duration_picker::update(msg, &mut model.report_duration);
            validation::validate_report_and_purge(&mut model.report_duration, &mut model.purge_duration);
        }
        Msg::PurgeDurationPicker(msg) => {
            duration_picker::update(msg, &mut model.purge_duration);
            validation::validate_report_and_purge(&mut model.report_duration, &mut model.purge_duration);
        }
        Msg::SubmitScan => {
            model.scanning = true;

            let query = stratagem::fast_file_scan::build(
                &model.fsname,
                model
                    .report_duration
                    .value_as_ms()
                    .map(Duration::from_millis)
                    .map(|x| humantime::format_duration(x).to_string()),
                model
                    .purge_duration
                    .value_as_ms()
                    .map(Duration::from_millis)
                    .map(|x| humantime::format_duration(x).to_string()),
            );

            let req = fetch::Request::graphql_query(&query);

            orders.perform_cmd(req.fetch_json_data(Msg::Scanned));
        }
        Msg::Scanned(x) => {
            match x {
                Ok(Response::Data(x)) => {
                    let x = command_modal::Input::Commands(vec![Arc::new(x.data.stratagem.run_fast_file_scan)]);

                    orders.send_g_msg(GMsg::OpenCommandModal(x));
                }
                Ok(Response::Errors(e)) => {
                    error!("An error has occurred during Stratagem scan: ", e);
                }
                Err(err) => {
                    error!("An error has occurred during Stratagem scan: ", err);
                    orders.skip();
                }
            }

            model.scanning = false;
            model.report_duration.reset();
            model.purge_duration.reset();
            orders.proxy(Msg::Modal).send_msg(modal::Msg::Close);
        }
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::Noop => {}
    };
}

pub(crate) fn view(model: &Model) -> Node<Msg> {
    let input_cls = class![
        C.appearance_none,
        C.focus__outline_none,
        C.focus__shadow_outline,
        C.px_3,
        C.py_2,
        C.rounded_sm,
        C.text_gray_800,
        C.bg_gray_200,
        C.col_span_5,
    ];

    let mut scan_btn = scan_now_button(model.scanning);
    if model.report_duration.validation_message.is_some() || model.purge_duration.validation_message.is_some() {
        scan_btn = scan_btn
            .merge_attrs(attrs! {
                At::Disabled => "disabled"
            })
            .merge_attrs(class![C.opacity_50]);
    }

    modal::bg_view(
        model.modal.open,
        Msg::Modal,
        modal::content_view(
            Msg::Modal,
            div![
                modal::title_view(
                    Msg::Modal,
                    span![
                        "Scan Filesystem Now",
                        font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_2], "chart-bar")
                    ]
                ),
                label![
                    attrs! {At::For => "report_duration"},
                    "Generate report for files older than:"
                ],
                duration_picker::view(
                    &model.report_duration,
                    input![
                        &input_cls,
                        attrs! {
                            At::Id => "report_duration",
                            At::AutoFocus => true,
                            At::Placeholder => "Optional",
                        },
                    ],
                )
                .merge_attrs(class![C.grid, C.grid_cols_6, C.mb_2])
                .map_msg(Msg::ReportDurationPicker),
                label![attrs! {At::For => "purge_duration"}, "Purge files older than:"],
                duration_picker::view(
                    &model.purge_duration,
                    input![
                        &input_cls,
                        attrs! {
                            At::Id => "purge_duration",
                            At::Placeholder => "Optional",
                        },
                    ],
                )
                .merge_attrs(class![C.grid, C.grid_cols_6])
                .map_msg(Msg::PurgeDurationPicker),
                modal::footer_view(vec![scan_btn, cancel_button()]).merge_attrs(class![C.pt_8]),
            ],
        )
        .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
            key_codes::ESC => Msg::Modal(modal::Msg::Close),
            _ => Msg::Noop,
        }))
        .merge_attrs(class![C.text_black]),
    )
}

fn cancel_button() -> Node<Msg> {
    button![
        class![
            C.bg_transparent,
            C.hover__bg_gray_100,
            C.py_2,
            C.px_4,
            C.ml_2,
            C.rounded_full,
            C.text_blue_500,
            C.hover__text_blue_400
        ],
        simple_ev(Ev::Click, modal::Msg::Close),
        "Cancel",
    ]
    .map_msg(Msg::Modal)
}

fn scan_now_button(scanning: bool) -> Node<Msg> {
    let spinner = if scanning {
        font_awesome(class![C.w_4, C.h_4, C.inline, C.pulse, C.ml_2], "spinner")
    } else {
        empty![]
    };

    let mut btn = button![
        class![
            C.bg_blue_500,
            C.hover__bg_blue_400,
            C.py_2,
            C.px_4,
            C.rounded_full,
            C.text_white,
        ],
        simple_ev(Ev::Click, Msg::SubmitScan),
        "Scan Now",
        spinner,
    ];

    if scanning {
        btn = btn
            .merge_attrs(attrs! {At::Disabled => true})
            .merge_attrs(class![C.cursor_not_allowed, C.opacity_50]);
    }

    btn
}
