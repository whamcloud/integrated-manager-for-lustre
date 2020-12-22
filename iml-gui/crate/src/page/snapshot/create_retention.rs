// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome, modal, Placement},
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
use iml_wire_types::{
    snapshot::ReserveUnit, warp_drive::ArcCache, warp_drive::ArcRecord, warp_drive::RecordId, Filesystem,
};
use seed::{prelude::*, *};
use std::{str::FromStr, sync::Arc};

#[derive(Debug)]
pub struct Model {
    submitting: bool,
    filesystems: Vec<Arc<Filesystem>>,
    fs_name: String,
    reserve_value: u32,
    reserve_unit: ReserveUnit,
    keep_num: Option<u32>,
    pub modal: modal::Model,
}

impl Default for Model {
    fn default() -> Self {
        Model {
            submitting: false,
            filesystems: vec![],
            fs_name: "".into(),
            reserve_value: 0,
            reserve_unit: ReserveUnit::Percent,
            keep_num: None,
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
    KeepNumChanged(String),
    FsNameChanged(String),
    ReserveValueChanged(String),
    ReserveUnitChanged(String),
    Submit,
    SnapshotCreateRetentionResp(fetch::ResponseDataResult<Response<snapshot::create_retention::Resp>>),
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
        Msg::KeepNumChanged(x) => {
            model.keep_num = x.parse().ok();
        }
        Msg::ReserveValueChanged(x) => {
            model.reserve_value = x.parse().unwrap();
        }
        Msg::ReserveUnitChanged(x) => {
            model.reserve_unit = ReserveUnit::from_str(&x).unwrap();
        }
        Msg::Submit => {
            model.submitting = true;

            let query = snapshot::create_retention::build(
                &model.fs_name,
                model.reserve_value,
                model.reserve_unit,
                model.keep_num,
            );

            let req = fetch::Request::graphql_query(&query);

            orders.perform_cmd(req.fetch_json_data(Msg::SnapshotCreateRetentionResp));
        }
        Msg::SnapshotCreateRetentionResp(x) => {
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
                    error!("An error has occurred during policy creation: ", e);
                }
                Err(e) => {
                    error!("An error has occurred during policy creation: ", e);
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
                modal::title_view(Msg::Modal, span!["Create Snapshot Retention Policy"]),
                form![
                    ev(Ev::Submit, move |event| {
                        event.prevent_default();
                        Msg::Submit
                    }),
                    div![
                        class![C.grid, C.grid_cols_2, C.gap_4, C.p_4, C.items_center],
                        label![attrs! {At::For => "retention_fs_name"}, "Filesystem Name"],
                        div![
                            class![C.inline_block, C.relative, C.bg_gray_200],
                            select![
                                id!["retention_fs_name"],
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
                            attrs! {At::For => "reserve_value"},
                            "Reserve",
                            help_indicator(
                                "Delete the oldest snapshot when available space falls below this value.",
                                Placement::Right
                            )
                        ],
                        div![
                            class![C.grid, C.grid_cols_6],
                            input![
                                &input_cls,
                                class![C.bg_gray_200, C.text_gray_800, C.col_span_4, C.rounded_r_none],
                                id!["reserve_value"],
                                attrs! {
                                    At::Type => "number",
                                    At::Min => "0",
                                    At::Placeholder => "Required",
                                    At::Required => true.as_at_value(),
                                },
                                input_ev(Ev::Change, Msg::ReserveValueChanged),
                            ],
                            div![
                                class![C.inline_block, C.relative, C.col_span_2, C.text_white, C.bg_blue_500],
                                select![
                                    id!["reserve_unit"],
                                    &input_cls,
                                    class![C.w_full, C.h_full C.rounded_l_none, C.bg_transparent],
                                    option![class![C.font_sans], attrs! {At::Value => "percent"}, "%"],
                                    option![class![C.font_sans], attrs! {At::Value => "gibibytes"}, "GiB"],
                                    option![class![C.font_sans], attrs! {At::Value => "tebibytes"}, "TiB"],
                                    attrs! {
                                        At::Required => true.as_at_value(),
                                    },
                                    input_ev(Ev::Change, Msg::ReserveUnitChanged),
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
                            attrs! {At::For => "keep_num"},
                            "Minimum Snapshots",
                            help_indicator("Minimum number of snapshots to keep", Placement::Right)
                        ],
                        input![
                            &input_cls,
                            class![C.bg_gray_200, C.text_gray_800, C.rounded_r_none],
                            id!["keep_num"],
                            attrs! {
                                At::Type => "number",
                                At::Min => "0",
                                At::Placeholder => "Optional (default: 0)",
                                At::Required => false.as_at_value(),
                            },
                            input_ev(Ev::Change, Msg::KeepNumChanged),
                        ],
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
                            "Create Policy",
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
