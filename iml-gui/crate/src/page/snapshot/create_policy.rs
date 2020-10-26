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

#[derive(Debug, Default)]
pub struct Model {
    pub modal: modal::Model,
    submitting: bool,
    filesystems: Vec<Arc<Filesystem>>,

    interval: i32,
    interval_unit: String,
    vars: snapshot::policy::create::Vars,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, _: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        orders.send_msg(Msg::SetFilesystems(cache.filesystem.values().cloned().collect()));
    }
    fn remove_record(&mut self, _: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        orders.send_msg(Msg::SetFilesystems(cache.filesystem.values().cloned().collect()));

        let present = cache.filesystem.values().any(|x| x.name == self.vars.filesystem);

        if !present {
            let x = get_fs_names(cache).into_iter().next().unwrap_or_default();
            orders.send_msg(Msg::Input(Input::Filesystem(x)));
        }
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        orders.send_msg(Msg::SetFilesystems(cache.filesystem.values().cloned().collect()));

        let x = get_fs_names(cache).into_iter().next().unwrap_or_default();
        orders.send_msg(Msg::Input(Input::Filesystem(x)));
        orders.send_msg(Msg::Input(Input::IntervalUnit("days".to_string())));
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Modal(modal::Msg),
    Open,
    Close,
    SetFilesystems(Vec<Arc<Filesystem>>),
    Input(Input),
    Submit,
    CreatePolicyResp(fetch::ResponseDataResult<Response<snapshot::policy::create::Resp>>),
    Noop,
}

#[derive(Clone, Debug)]
pub enum Input {
    Filesystem(String),
    Interval(i32),
    IntervalUnit(String),
    ToggleBarrier,
    Keep(i32),
    Daily(Option<i32>),
    Monthly(Option<i32>),
    Weekly(Option<i32>),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SetFilesystems(x) => {
            model.filesystems = x;
        }
        Msg::Input(x) => match x {
            Input::Interval(i) => model.interval = i,
            Input::IntervalUnit(i) => model.interval_unit = i,

            Input::Filesystem(i) => model.vars.filesystem = i,
            Input::ToggleBarrier => model.vars.barrier = Some(!model.vars.barrier.unwrap_or(false)),
            Input::Keep(i) => model.vars.keep = i,
            Input::Daily(i) => model.vars.daily = i,
            Input::Weekly(i) => model.vars.weekly = i,
            Input::Monthly(i) => model.vars.monthly = i,
        },
        Msg::Submit => {
            model.submitting = true;
            model.vars.interval = format!("{}{}", model.interval, model.interval_unit);

            let query = snapshot::policy::create::build(model.vars.clone());

            let req = fetch::Request::graphql_query(&query);

            orders.perform_cmd(req.fetch_json_data(|x| Msg::CreatePolicyResp(x)));
        }
        Msg::CreatePolicyResp(x) => {
            model.submitting = false;
            orders.send_msg(Msg::Close);

            match x {
                Ok(Response::Data(_)) => {}
                Ok(Response::Errors(e)) => {
                    error!("An error has occurred during policy creation: ", e);
                }
                Err(e) => {
                    error!("An error has occurred during policy creation: ", e);
                }
            }
        }
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::Open => {
            model.modal.open = true;
        }
        Msg::Close => {
            model.modal.open = false;
        }
        Msg::Noop => {}
    };
}

// FIXME: this function was created to help rustfmt only
fn interval_unit_options(selected: &str) -> Vec<Node<Msg>> {
    vec![
        option![
            class![C.font_sans],
            attrs! {At::Value => "minutes", At::Selected => (selected == "minutes").as_at_value()},
            "Minutes"
        ],
        option![
            class![C.font_sans],
            attrs! {At::Value => "hours", At::Selected => (selected == "hours").as_at_value()},
            "Hours"
        ],
        option![
            class![C.font_sans],
            attrs! {At::Value => "days", At::Selected => (selected == "days").as_at_value()},
            "Days"
        ],
        option![
            class![C.font_sans],
            attrs! {At::Value => "years", At::Selected => (selected == "years").as_at_value()},
            "Years"
        ],
    ]
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
                modal::title_view(Msg::Modal, span!["Create Automatic Snapshot Policy"]),
                form![
                    ev(Ev::Submit, move |event| {
                        event.prevent_default();
                        Msg::Submit
                    }),
                    div![
                        class![C.grid, C.grid_cols_2, C.gap_4, C.p_4, C.items_center],
                        label![attrs! {At::For => "policy_filesystem"}, "Filesystem Name"],
                        div![
                            class![C.inline_block, C.relative, C.bg_gray_200],
                            select![
                                id!["policy_filesystem"],
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
                                    if x.name == model.vars.filesystem.as_str() {
                                        opt.add_attr(At::Selected.to_string(), "selected");
                                    }

                                    opt
                                }),
                                attrs! {
                                    At::Required => true.as_at_value(),
                                },
                                input_ev(Ev::Change, |s| Msg::Input(Input::Filesystem(s))),
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
                            attrs! {At::For => "policy_interval"},
                            "Interval",
                            help_indicator("How often to take a snapshot for a selected filesystem", Placement::Right)
                        ],
                        div![
                            class![C.grid, C.grid_cols_6],
                            input![
                                &input_cls,
                                class![C.bg_gray_200, C.text_gray_800, C.col_span_4, C.rounded_r_none],
                                id!["policy_interval"],
                                attrs! {
                                    At::Type => "number",
                                    At::Min => "1",
                                    At::Placeholder => "Required",
                                    At::Required => true.as_at_value(),
                                },
                                input_ev(Ev::Change, |s| s
                                    .parse()
                                    .map(|i| Msg::Input(Input::Interval(i)))
                                    .unwrap_or(Msg::Noop)),
                            ],
                            div![
                                class![C.inline_block, C.relative, C.col_span_2, C.text_white, C.bg_blue_500],
                                select![
                                    id!["interval_unit"],
                                    &input_cls,
                                    class![C.w_full, C.h_full C.rounded_l_none, C.bg_transparent],
                                    interval_unit_options(&model.interval_unit),
                                    attrs! {
                                        At::Required => true.as_at_value(),
                                    },
                                    input_ev(Ev::Change, |s| Msg::Input(Input::IntervalUnit(s))),
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
                            attrs! {At::For => "policy_keep"},
                            "Keep Recent Snapshots",
                            help_indicator("Number of the most recent snapshots to keep", Placement::Right)
                        ],
                        input![
                            &input_cls,
                            class![C.bg_gray_200, C.text_gray_800, C.rounded_r_none],
                            id!["policy_keep"],
                            attrs! {
                                At::Type => "number",
                                At::Min => "1",
                                At::Placeholder => "Required",
                                At::Required => true.as_at_value(),
                            },
                            input_ev(Ev::Change, |s| s
                                .parse()
                                .map(|i| Msg::Input(Input::Keep(i)))
                                .unwrap_or(Msg::Noop)),
                        ],
                        label![
                            attrs! {At::For => "policy_daily"},
                            "Daily Snapshots",
                            help_indicator(
                                "Number of days when keep the most recent snapshot of each day",
                                Placement::Right
                            )
                        ],
                        input![
                            &input_cls,
                            class![C.bg_gray_200, C.text_gray_800, C.rounded_r_none],
                            id!["policy_daily"],
                            attrs! {
                                At::Type => "number",
                                At::Min => "0",
                                At::Placeholder => "Optional",
                                At::Required => false.as_at_value(),
                            },
                            input_ev(Ev::Change, |s| Msg::Input(Input::Daily(s.parse().ok()))),
                        ],
                        label![
                            attrs! {At::For => "policy_weekly"},
                            "Weekly Snapshots",
                            help_indicator(
                                "Number of weeks when keep the most recent snapshot of each week",
                                Placement::Right
                            )
                        ],
                        input![
                            &input_cls,
                            class![C.bg_gray_200, C.text_gray_800, C.rounded_r_none],
                            id!["policy_weekly"],
                            attrs! {
                                At::Type => "number",
                                At::Min => "0",
                                At::Placeholder => "Optional",
                                At::Required => false.as_at_value(),
                            },
                            input_ev(Ev::Change, |s| Msg::Input(Input::Weekly(s.parse().ok()))),
                        ],
                        label![
                            attrs! {At::For => "policy_monthly"},
                            "Monthly Snapshots",
                            help_indicator(
                                "Number of months when keep the most recent snapshot of each months",
                                Placement::Right
                            )
                        ],
                        input![
                            &input_cls,
                            class![C.bg_gray_200, C.text_gray_800, C.rounded_r_none],
                            id!["policy_monthly"],
                            attrs! {
                                At::Type => "number",
                                At::Min => "0",
                                At::Placeholder => "Optional",
                                At::Required => false.as_at_value(),
                            },
                            input_ev(Ev::Change, |s| Msg::Input(Input::Monthly(s.parse().ok()))),
                        ],
                        label![
                            attrs! {At::For => "policy_barrier"},
                            "Use Barrier",
                            help_indicator("Set write barrier before creating snapshot", Placement::Right)
                        ],
                        form::toggle()
                            .merge_attrs(id!["policy_barrier"])
                            .merge_attrs(attrs! {
                               At::Checked => model.vars.barrier.unwrap_or(false).as_at_value()
                            })
                            .with_listener(input_ev(Ev::Change, |_| Msg::Input(Input::ToggleBarrier))),
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
