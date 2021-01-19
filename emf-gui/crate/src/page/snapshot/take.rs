// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use super::*;
use crate::{components::command_modal, components::font_awesome, extensions::RequestExt};

#[derive(Clone, Debug)]
pub enum Msg {
    Submit,
    NameChange(String),
    CommentChange(String),
    SetFilesystems(Vec<Arc<Filesystem>>),
    FsNameChanged(String),
    BarrierChanged(String),
    SnapshotCreateResp(fetch::ResponseDataResult<Response<snapshot::create::Resp>>),
}

#[derive(Default, Debug)]
pub struct Model {
    fs_name: String,
    filesystems: Vec<Arc<Filesystem>>,
    barrier: bool,
    name: String,
    comment: Option<String>,
    submitting: bool,
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

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Submit => {
            model.submitting = true;

            let query =
                snapshot::create::build(&model.fs_name, &model.name, model.comment.as_ref(), Some(model.barrier));

            let req = fetch::Request::graphql_query(&query);

            orders.perform_cmd(req.fetch_json_data(|x| Msg::SnapshotCreateResp(x)));
        }
        Msg::SnapshotCreateResp(x) => match x {
            Ok(Response::Data(x)) => {
                let x = command_modal::Input::Commands(vec![Arc::new(x.data.create_snapshot)]);

                orders.send_g_msg(GMsg::OpenCommandModal(x));

                *model = Model {
                    fs_name: model.fs_name.to_string(),
                    ..Model::default()
                };
            }
            Ok(Response::Errors(e)) => {
                error!("An error has occurred during Snapshot creation: ", e);

                model.submitting = false;
            }
            Err(e) => {
                error!("An error has occurred during Snapshot creation: ", e);

                model.submitting = false;
            }
        },
        Msg::SetFilesystems(x) => {
            model.filesystems = x;
        }
        Msg::NameChange(x) => {
            model.name = x;
        }
        Msg::CommentChange(x) => {
            model.comment = Some(x);
        }
        Msg::FsNameChanged(x) => {
            model.fs_name = x;
        }
        Msg::BarrierChanged(_) => {
            model.barrier = !model.barrier;
        }
    }
}

pub fn init(cache: &ArcCache, model: &mut Model) {
    let fs_name = get_fs_names(cache).into_iter().next();

    if let Some(fs_name) = fs_name {
        model.fs_name = fs_name.to_string();
    }
}

pub fn view(model: &Model) -> Node<Msg> {
    let input_cls = class![
        C.appearance_none,
        C.focus__outline_none,
        C.focus__shadow_outline,
        C.px_3,
        C.py_2,
        C.rounded_sm,
        C.text_gray_800
    ];

    panel::view(
        h3![
            class![C.py_4, C.font_normal, C.text_lg],
            "Take Manual Snapshot",
            help_indicator("Take an ad-hoc filesystem snapshot", Placement::Right),
        ],
        div![
            class![C.items_center],
            form![
                class![C.grid, C.grid_cols_2, C.gap_4, C.p_4, C.items_center],
                ev(Ev::Submit, move |event| {
                    event.prevent_default();
                    Msg::Submit
                }),
                label![attrs! {At::For => "fs_name"}, "FS Name"],
                div![
                    class![C.inline_block, C.relative, C.bg_gray_200],
                    select![
                        id!["fs_name"],
                        &input_cls,
                        class![C.block, C.leading_tight, C.bg_transparent, C.pr_8, C.rounded, C.w_full,],
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
                    attrs! {At::For => "snapshot_name"},
                    "Snapshot Name",
                    help_indicator("The snapshot name. ' ', '&' and '/' are disallowed", Placement::Right)
                ],
                input![
                    &input_cls,
                    class![C.bg_gray_200],
                    input_ev(Ev::Input, Msg::NameChange),
                    attrs! {
                        At::Id => "snapshot_name",
                        At::AutoFocus => true.as_at_value(),
                        At::Required => true.as_at_value(),
                        At::Pattern => "[^ &/,]+",
                        At::Placeholder => "Required",
                        At::Type => "text",
                        At::Value => &model.name
                    },
                ],
                label![
                    attrs! {At::For => "snapshot_comment"},
                    "Comment",
                    help_indicator("A description for the purpose of the snapshot", Placement::Right)
                ],
                input![
                    &input_cls,
                    class![C.bg_gray_200],
                    id!["snapshot_comment"],
                    input_ev(Ev::Input, Msg::CommentChange),
                    attrs! {
                        At::Placeholder => "Optional",
                        At::Value => model.comment.as_deref().unwrap_or_default()
                    }
                ],
                label![
                    attrs! {At::For => "barrier"},
                    "Use Barrier",
                    help_indicator("Set write barrier before creating snapshot", Placement::Right)
                ],
                form::toggle()
                    .merge_attrs(id!["barrier"])
                    .merge_attrs(attrs! {
                       At::Checked => model.barrier.as_at_value()
                    })
                    .with_listener(input_ev(Ev::Change, Msg::BarrierChanged)),
                button![
                    class![
                        C.bg_blue_500,
                        C.col_span_2,
                        C.duration_300,
                        C.disabled__bg_gray_500,
                        C.disabled__cursor_not_allowed,
                        C.focus__outline_none,
                        C.form_invalid__bg_gray_500,
                        C.form_invalid__cursor_not_allowed,
                        C.form_invalid__pointer_events_none,
                        C.px_6,
                        C.py_2,
                        C.rounded_sm,
                        C.text_white,
                        C.transition_colors,
                    ],
                    attrs! {
                        At::Disabled => model.submitting.as_at_value()
                    },
                    font_awesome_outline(class![C.h_4, C.w_4, C.mr_1, C.inline], "check-circle"),
                    "Take Snapshot",
                ],
            ]
        ],
    )
}
