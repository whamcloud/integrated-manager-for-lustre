// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::font_awesome,
    components::{attrs, font_awesome_outline, form, paging, panel, resource_links, table, tooltip, Placement},
    extensions::{MergeAttrs as _, NodeExt as _},
    generated::css_classes::C,
    page::RecordChange,
    GMsg,
};
use iml_graphql_queries::{snapshot, Response};
use iml_wire_types::{
    snapshot::SnapshotRecord,
    warp_drive::{ArcCache, ArcRecord, RecordId},
    Filesystem,
};
use seed::{prelude::*, *};
use std::{cmp::Ordering, ops::Deref, sync::Arc};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortField {
    CreationTime,
    Name,
}

impl Default for SortField {
    fn default() -> Self {
        Self::CreationTime
    }
}

#[derive(Default, Debug)]
pub struct Model {
    pager: paging::Model,
    rows: Vec<Arc<SnapshotRecord>>,
    sort: (SortField, paging::Dir),
    take: take::Model,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, _: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
    fn remove_record(&mut self, _: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Page(paging::Msg),
    Sort,
    SortBy(table::SortBy<SortField>),
    Take(take::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SortBy(table::SortBy(x)) => {
            let dir = if x == model.sort.0 {
                model.sort.1.next()
            } else {
                paging::Dir::default()
            };

            model.sort = (x, dir);

            orders.send_msg(Msg::Sort);
        }
        Msg::Page(msg) => {
            paging::update(msg, &mut model.pager, &mut orders.proxy(Msg::Page));
        }
        Msg::Sort => {
            let sort_fn = match model.sort {
                (SortField::Name, paging::Dir::Asc) => Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                    natord::compare(&a.snapshot_name, &b.snapshot_name)
                })
                    as Box<dyn FnMut(&Arc<SnapshotRecord>, &Arc<SnapshotRecord>) -> Ordering>,
                (SortField::Name, paging::Dir::Desc) => Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                    natord::compare(&b.snapshot_name, &a.snapshot_name)
                }),
                (SortField::CreationTime, paging::Dir::Asc) => {
                    Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                        a.create_time.partial_cmp(&b.create_time).unwrap()
                    })
                }
                (SortField::CreationTime, paging::Dir::Desc) => {
                    Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                        b.create_time.partial_cmp(&a.create_time).unwrap()
                    })
                }
            };

            model.rows.sort_by(sort_fn);
        }
        Msg::Take(msg) => {
            take::update(msg, &mut model.take, &mut orders.proxy(Msg::Take));
        }
    }
}

pub fn init(cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    model.set_records(cache, orders);

    take::init(cache, &mut model.take);
}

pub fn view(model: &Model, cache: &ArcCache) -> impl View<Msg> {
    let fs_names = get_fs_names(cache);

    if fs_names.is_empty() {
        //TODO Replace with a messasge saying a filesystem must be created first.
        return div!["No filesystems found"];
    }

    div![
        take::view(&model.take, fs_names)
            .map_msg(Msg::Take)
            .merge_attrs(class![C.my_6]),
        panel::view(
            h3![class![C.py_4, C.font_normal, C.text_lg], "Snapshots"],
            div![
                table::wrapper_view(vec![
                    table::thead_view(vec![
                        table::sort_header("Name", SortField::Name, model.sort.0, model.sort.1).map_msg(Msg::SortBy),
                        table::th_view(plain!["FS Name"]),
                        table::sort_header("Creation Time", SortField::CreationTime, model.sort.0, model.sort.1)
                            .map_msg(Msg::SortBy),
                        table::th_view(plain!["Comment"]),
                        table::th_view(plain!["State"]),
                    ]),
                    tbody![model.rows[model.pager.range()].iter().map(|x| {
                        tr![
                            table::td_center(plain![x.snapshot_name.clone()]),
                            td![
                                table::td_cls(),
                                class![C.text_center],
                                match get_fs_by_name(cache, &x.filesystem_name) {
                                    Some(x) => {
                                        div![resource_links::fs_link(&x)]
                                    }
                                    None => {
                                        plain![x.filesystem_name.to_string()]
                                    }
                                }
                            ],
                            table::td_center(plain![x.create_time.format("%m/%d/%Y %H:%M:%S").to_string()]),
                            td![
                                table::td_cls(),
                                class![C.text_center],
                                x.comment.as_deref().unwrap_or("---")
                            ],
                            table::td_center(plain![match &x.mounted {
                                Some(true) => "mounted",
                                Some(false) => "unmounted",
                                None => "unknown",
                            }]),
                        ]
                    })]
                ])
                .merge_attrs(class![C.my_6]),
                div![
                    class![C.flex, C.justify_end, C.py_1, C.pr_3],
                    paging::limit_selection_view(&model.pager).map_msg(Msg::Page),
                    paging::page_count_view(&model.pager),
                    paging::next_prev_view(&model.pager).map_msg(Msg::Page)
                ]
            ],
        )
    ]
}

fn help_indicator<T>(msg: &str, placement: Placement) -> Node<T> {
    span![
        attrs::container(),
        class![C.inline_block, C.h_3, C.w_3, C.ml_2, C.cursor_pointer],
        font_awesome(class![C.text_blue_500], "question-circle")
            .with_style(St::Height, "inherit")
            .with_style(St::Width, "inherit"),
        tooltip::view(msg, placement)
    ]
}

fn get_fs_names<'a>(cache: &'a ArcCache) -> Vec<&'a str> {
    cache.filesystem.values().map(|x| x.name.as_str()).collect()
}

fn get_fs_by_name<'a>(cache: &'a ArcCache, name: &str) -> Option<&'a Filesystem> {
    cache.filesystem.values().find(|x| x.name == name).map(|x| x.deref())
}

mod take {
    use super::*;
    use crate::{components::command_modal, components::font_awesome, extensions::RequestExt};

    #[derive(Clone, Debug)]
    pub enum Msg {
        Submit,
        NameChange(String),
        CommentChange(String),
        FsNameChanged(String),
        BarrierChanged(String),
        SnapshotCreateResp(fetch::ResponseDataResult<Response<snapshot::create::Resp>>),
    }

    #[derive(Default, Debug)]
    pub struct Model {
        fs_name: String,
        barrier: bool,
        name: String,
        comment: Option<String>,
        submitting: bool,
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
                }
                Err(e) => {
                    error!("An error has occurred during Snapshot creation: ", e);

                    model.submitting = false;
                }
            },
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

    pub fn view(model: &Model, fs_names: Vec<&str>) -> Node<Msg> {
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
                "Take Snapshot",
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
                            fs_names.iter().map(|x| {
                                let mut opt = option![class![C.font_sans], attrs! {At::Value => x}, x];
                                if *x == model.fs_name.as_str() {
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
}
