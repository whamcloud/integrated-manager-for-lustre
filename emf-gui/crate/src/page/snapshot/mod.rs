// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod add_interval;
mod create_retention;
mod list;
mod list_interval;
mod list_retention;
mod take;

use crate::{
    components::{
        attrs, font_awesome, font_awesome_outline, form, paging, panel, resource_links, restrict, table, tooltip,
        Placement,
    },
    extensions::{MergeAttrs as _, NodeExt as _},
    generated::css_classes::C,
    page::RecordChange,
    GMsg,
};
use emf_graphql_queries::{snapshot, Response};
use emf_wire_types::{
    snapshot::SnapshotRecord,
    warp_drive::{ArcCache, ArcRecord, RecordId},
    Filesystem, GroupType, Session,
};
use seed::{prelude::*, *};
use std::{cmp::Ordering, ops::Deref, sync::Arc};

#[derive(Default, Debug)]
pub struct Model {
    take: take::Model,
    list_interval: list_interval::Model,
    list_retention: list_retention::Model,
    list: list::Model,
    add_interval: add_interval::Model,
    create_retention: create_retention::Model,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, record: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::List));

        self.list_interval
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::ListInterval));

        self.list_retention
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::ListRetention));

        self.add_interval
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::AddInterval));

        self.create_retention
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::CreatRetention));

        self.take.update_record(record, cache, &mut orders.proxy(Msg::Take));
    }
    fn remove_record(&mut self, record: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list.remove_record(record, cache, &mut orders.proxy(Msg::List));

        self.list_interval
            .remove_record(record, cache, &mut orders.proxy(Msg::ListInterval));

        self.list_retention
            .remove_record(record, cache, &mut orders.proxy(Msg::ListRetention));

        self.add_interval
            .remove_record(record, cache, &mut orders.proxy(Msg::AddInterval));

        self.create_retention
            .remove_record(record, cache, &mut orders.proxy(Msg::CreatRetention));

        self.take.remove_record(record, cache, &mut orders.proxy(Msg::Take));
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list.set_records(cache, &mut orders.proxy(Msg::List));

        self.list_interval
            .set_records(cache, &mut orders.proxy(Msg::ListInterval));

        self.list_retention
            .set_records(cache, &mut orders.proxy(Msg::ListRetention));

        self.add_interval
            .set_records(cache, &mut orders.proxy(Msg::AddInterval));

        self.create_retention
            .set_records(cache, &mut orders.proxy(Msg::CreatRetention));

        self.take.set_records(cache, &mut orders.proxy(Msg::Take));
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Take(take::Msg),
    ListInterval(list_interval::Msg),
    ListRetention(list_retention::Msg),
    List(list::Msg),
    AddInterval(add_interval::Msg),
    CreatRetention(create_retention::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Take(msg) => {
            take::update(msg, &mut model.take, &mut orders.proxy(Msg::Take));
        }
        Msg::ListInterval(msg) => {
            list_interval::update(msg, &mut model.list_interval, &mut orders.proxy(Msg::ListInterval));
        }
        Msg::ListRetention(msg) => {
            list_retention::update(msg, &mut model.list_retention, &mut orders.proxy(Msg::ListRetention));
        }
        Msg::List(msg) => {
            list::update(msg, &mut model.list, &mut orders.proxy(Msg::List));
        }
        Msg::AddInterval(msg) => {
            add_interval::update(msg, &mut model.add_interval, &mut orders.proxy(Msg::AddInterval));
        }
        Msg::CreatRetention(msg) => {
            create_retention::update(msg, &mut model.create_retention, &mut orders.proxy(Msg::CreatRetention));
        }
    }
}

pub fn init(cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    model.set_records(cache, orders);

    take::init(cache, &mut model.take);
}

pub fn view(model: &Model, cache: &ArcCache, session: Option<&Session>) -> impl View<Msg> {
    let fs_names = get_fs_names(cache);

    if fs_names.is_empty() {
        //TODO Replace with a messasge saying a filesystem must be created first.
        return div!["No filesystems found"];
    }

    div![
        take::view(&model.take).map_msg(Msg::Take).merge_attrs(class![C.my_6]),
        if cache.snapshot_interval.is_empty() {
            vec![add_interval_btn(false, session)]
        } else {
            vec![
                list_interval::view(&model.list_interval, cache, session)
                    .map_msg(Msg::ListInterval)
                    .merge_attrs(class![C.my_6]),
                add_interval_btn(true, session),
            ]
        },
        add_interval::view(&model.add_interval).map_msg(Msg::AddInterval),
        if cache.snapshot_retention.is_empty() {
            empty![]
        } else {
            list_retention::view(&model.list_retention, cache, session)
                .map_msg(Msg::ListRetention)
                .merge_attrs(class![C.my_6])
        },
        create_retention_btn(session),
        create_retention::view(&model.create_retention).map_msg(Msg::CreatRetention),
        list::view(&model.list, cache).map_msg(Msg::List)
    ]
}

fn add_interval_btn(has_intervals: bool, session: Option<&Session>) -> Node<Msg> {
    restrict::view(
        session,
        GroupType::FilesystemAdministrators,
        button![
            class![
                C.bg_blue_500,
                C.duration_300,
                C.flex,
                C.hover__bg_blue_400,
                C.items_center,
                C.mb_6,
                C.px_6,
                C.py_2,
                C.rounded_sm,
                C.text_white,
                C.transition_colors
            ],
            font_awesome(class![C.h_3, C.w_3, C.mr_1, C.inline], "plus"),
            if has_intervals {
                "Add Another Automated Snapshot Rule"
            } else {
                "Add Automated Snapshot Rule"
            },
            simple_ev(Ev::Click, add_interval::Msg::Open).map_msg(Msg::AddInterval)
        ],
    )
}

fn create_retention_btn(session: Option<&Session>) -> Node<Msg> {
    restrict::view(
        session,
        GroupType::FilesystemAdministrators,
        button![
            class![
                C.bg_blue_500,
                C.duration_300,
                C.flex,
                C.hover__bg_blue_400,
                C.items_center,
                C.mb_6,
                C.px_6,
                C.py_2,
                C.rounded_sm,
                C.text_white,
                C.transition_colors
            ],
            font_awesome(class![C.h_3, C.w_3, C.mr_1, C.inline], "plus"),
            "Create Snapshot Retention Policy",
            simple_ev(Ev::Click, create_retention::Msg::Open).map_msg(Msg::CreatRetention)
        ],
    )
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

fn get_fs_names(cache: &ArcCache) -> Vec<String> {
    cache.filesystem.values().map(|x| x.name.to_string()).collect()
}

fn get_fs_by_name<'a>(cache: &'a ArcCache, name: &str) -> Option<&'a Filesystem> {
    cache.filesystem.values().find(|x| x.name == name).map(|x| x.deref())
}
