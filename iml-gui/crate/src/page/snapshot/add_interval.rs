// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome, form, modal, Placement},
    extensions::{MergeAttrs as _, NodeExt as _},
    generated::css_classes::C,
    key_codes,
    page::{
        snapshot::{get_fs_names, help_indicator},
        RecordChange,
    },
    GMsg, RequestExt,
};
use iml_graphql_queries::{snapshot, Response};
use iml_wire_types::{warp_drive::ArcCache, warp_drive::ArcRecord, warp_drive::RecordId, Filesystem};
use seed::{prelude::*, *};
use std::sync::Arc;

#[derive(Debug)]
pub struct Model {
    submitting: bool,
    filesystems: Vec<Arc<Filesystem>>,
    fs_name: String,
    barrier: bool,
    interval_value: String,
    interval_unit: String,
    pub modal: modal::Model,
}

impl Default for Model {
    fn default() -> Self {
        Model {
            submitting: false,
            filesystems: vec![],
            fs_name: "".into(),
            barrier: false,
            interval_value: "".into(),
            interval_unit: "d".into(),
            modal: modal::Model::default(),
        }
    }
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, _: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        orders.send_msg(Msg::SetFilesystems(cache.filesystem.values().cloned().collect()));
    }
    fn remove_record(&mut self, _: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        orders.send_msg(Msg::SetFilesystems(cache.filesystem.values().cloned().collect()));

        let present = cache.filesystem.values().any(|x| x.name == self.fs_name);

        if !present {
            let x = get_fs_names(cache).into_iter().next().unwrap_or_default();
            orders.send_msg(Msg::FsNameChanged(x));
        }
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        orders.send_msg(Msg::SetFilesystems(cache.filesystem.values().cloned().collect()));

        let x = get_fs_names(cache).into_iter().next().unwrap_or_default();
        orders.send_msg(Msg::FsNameChanged(x));
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Modal(modal::Msg),
    Open,
    Close,
    SetFilesystems(Vec<Arc<Filesystem>>),
    BarrierChanged(String),
    FsNameChanged(String),
    IntervalValueChanged(String),
    IntervalUnitChanged(String),
    Submit,
    SnapshotCreateIntervalResp(fetch::ResponseDataResult<Response<snapshot::create_interval::Resp>>),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::Open => {
            model.modal.open = true;
        }
        Msg::Close => {
            model.modal.open = false;
        }
        Msg::SetFilesystems(x) => {
            model.filesystems = x;
        }
        Msg::FsNameChanged(x) => {
            model.fs_name = x;
        }
        Msg::BarrierChanged(_) => {
            model.barrier = !model.barrier;
        }
        Msg::IntervalValueChanged(x) => {
            model.interval_value = x;
        }
        Msg::IntervalUnitChanged(x) => {
            model.interval_unit = x;
        }
        Msg::Submit => {
            model.submitting = true;

            let interval = format!("{}{}", model.interval_value.trim(), model.interval_unit);

            let query = snapshot::create_interval::build(&model.fs_name, interval, Some(model.barrier));

            let req = fetch::Request::graphql_query(&query);

            orders.perform_cmd(req.fetch_json_data(Msg::SnapshotCreateIntervalResp));
        }
        Msg::SnapshotCreateIntervalResp(x) => {
            model.submitting = false;
            orders.send_msg(Msg::Close);

            match x {
                Ok(Response::Data(_)) => {
                    *model = Model {
                        fs_name: model.fs_name.to_string(),
                        ..Model::default()
                    };
                }
                Ok(Response::Errors(e)) => {
                    error!("An error has occurred during Snapshot Interval creation: ", e);
                }
                Err(e) => {
                    error!("An error has occurred during Snapshot Interval creation: ", e);
                }
            }
        }
        Msg::Noop => {}
    };
}

pub fn view(model: &Model) -> Node<Msg> {
    let input_cls = class![
        C.appearance_none,
        C.focus__outline_none,
        C.focus__shadow_outline,
        C.px_3,
        C.py_2,
        C.rounded_sm
    ];

    modal::bg_view(
        model.modal.open,
        Msg::Modal,
        modal::content_view(
            Msg::Modal,
            div![
                modal::title_view(Msg::Modal, span!["Add Automated Snapshot Rule"]),
                form![
                    ev(Ev::Submit, move |event| {
                        event.prevent_default();
                        Msg::Submit
                    }),
                    div![
                        class![C.grid, C.grid_cols_2, C.gap_4, C.p_4, C.items_center],
                        label![attrs! {At::For => "interval_fs_name"}, "Filesystem Name"],
                        div![
                            class![C.inline_block, C.relative, C.bg_gray_200],
                            select![
                                id!["interval_fs_name"],
                                &input_cls,
                                class![
                                    C.block,
                                    C.text_gray_800,
                                    C.leading_tight,
                                    C.bg_transparent,
                                    C.pr_8,
                                    C.rounded,
                                    C.w_full
                                ],
                                model.filesystems.iter().map(|x| {
                                    let mut opt = option![class![C.font_sans], attrs! {At::Value => x.name}, x.name];
                                    if x.name == model.fs_name.as_str() {
                                        opt.add_attr(At::Selected.to_string(), "selected");
                                    }

                                    opt
                                }),
                                attrs! {
                                    At::Required => true.as_at_value(),
                                },
                                input_ev(Ev::Change, Msg::FsNameChanged),
                            ],
                            div![
                                class![
                                    C.pointer_events_none,
                                    C.absolute,
                                    C.inset_y_0,
                                    C.right_0,
                                    C.flex,
                                    C.items_center,
                                    C.px_2,
                                    C.text_gray_700,
                                ],
                                font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "chevron-down")
                            ],
                        ],
                        label![
                            attrs! {At::For => "interval_value"},
                            "Interval",
                            help_indicator("How often to take snapshot for selected filesystem", Placement::Right)
                        ],
                        div![
                            class![C.grid, C.grid_cols_6],
                            input![
                                &input_cls,
                                class![C.bg_gray_200, C.text_gray_800, C.col_span_4, C.rounded_r_none],
                                id!["interval_value"],
                                attrs! {
                                    At::Type => "number",
                                    At::Min => "1",
                                    At::Placeholder => "Required",
                                    At::Required => true.as_at_value(),
                                },
                                input_ev(Ev::Change, Msg::IntervalValueChanged),
                            ],
                            div![
                                class![C.inline_block, C.relative, C.col_span_2, C.text_white, C.bg_blue_500],
                                select![
                                    id!["interval_unit"],
                                    &input_cls,
                                    class![C.w_full, C.h_full C.rounded_l_none, C.bg_transparent],
                                    option![class![C.font_sans], attrs! {At::Value => "d"}, "Days"],
                                    option![class![C.font_sans], attrs! {At::Value => "y"}, "Years"],
                                    option![class![C.font_sans], attrs! {At::Value => "m"}, "Minutes"],
                                    attrs! {
                                        At::Required => true.as_at_value(),
                                    },
                                    input_ev(Ev::Change, Msg::IntervalUnitChanged),
                                ],
                                div![
                                    class![
                                        C.pointer_events_none,
                                        C.absolute,
                                        C.inset_y_0,
                                        C.right_0,
                                        C.flex,
                                        C.items_center,
                                        C.px_2,
                                        C.text_white,
                                    ],
                                    font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "chevron-down")
                                ]
                            ],
                        ],
                        label![
                            attrs! {At::For => "interval_barrier"},
                            "Use Barrier",
                            help_indicator("Set write barrier before creating snapshot", Placement::Right)
                        ],
                        form::toggle()
                            .merge_attrs(id!["interval_barrier"])
                            .merge_attrs(attrs! {
                               At::Checked => model.barrier.as_at_value()
                            })
                            .with_listener(input_ev(Ev::Change, Msg::BarrierChanged)),
                    ],
                    modal::footer_view(vec![
                        button![
                            class![
                                C.bg_blue_500,
                                C.duration_300,
                                C.flex,
                                C.form_invalid__bg_gray_500,
                                C.form_invalid__cursor_not_allowed,
                                C.form_invalid__pointer_events_none,
                                C.hover__bg_blue_400,
                                C.items_center
                                C.px_4,
                                C.py_2,
                                C.rounded_full,
                                C.text_white,
                                C.transition_colors,
                            ],
                            font_awesome(class![C.h_3, C.w_3, C.mr_1, C.inline], "plus"),
                            "Add Rule",
                        ],
                        button![
                            class![
                                C.bg_transparent,
                                C.duration_300,
                                C.hover__bg_gray_100,
                                C.hover__text_blue_400,
                                C.ml_2,
                                C.px_4,
                                C.py_2,
                                C.rounded_full,
                                C.text_blue_500,
                                C.transition_colors,
                            ],
                            simple_ev(Ev::Click, modal::Msg::Close),
                            "Cancel",
                        ]
                        .map_msg(Msg::Modal),
                    ])
                    .merge_attrs(class![C.pt_8])
                ]
            ],
        )
        .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
            key_codes::ESC => Msg::Modal(modal::Msg::Close),
            _ => Msg::Noop,
        })),
    )
}
