// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod create_policy;
mod list;
mod list_policy;
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
use iml_graphql_queries::{snapshot, Response};
use iml_wire_types::{
    snapshot::SnapshotRecord,
    warp_drive::{ArcCache, ArcRecord, RecordId},
    Filesystem, GroupType, Session,
};
use seed::{prelude::*, *};
use std::{cmp::Ordering, ops::Deref, sync::Arc};

#[derive(Default, Debug)]
pub struct Model {
    take: take::Model,
    list: list::Model,
    create_policy: create_policy::Model,
    list_policy: list_policy::Model,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, record: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::List));

        self.take
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::Take));

        self.list_policy
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::ListPolicy));
        self.create_policy
            .update_record(record, cache, &mut orders.proxy(Msg::CreatePolicy));
    }
    fn remove_record(&mut self, record: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list.remove_record(record, cache, &mut orders.proxy(Msg::List));

        self.take.remove_record(record, cache, &mut orders.proxy(Msg::Take));

        self.list_policy
            .remove_record(record, cache, &mut orders.proxy(Msg::ListPolicy));
        self.create_policy
            .remove_record(record, cache, &mut orders.proxy(Msg::CreatePolicy));
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list.set_records(cache, &mut orders.proxy(Msg::List));

        self.take.set_records(cache, &mut orders.proxy(Msg::Take));

        self.list_policy.set_records(cache, &mut orders.proxy(Msg::ListPolicy));
        self.create_policy
            .set_records(cache, &mut orders.proxy(Msg::CreatePolicy));
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Take(take::Msg),
    List(list::Msg),
    CreatePolicy(create_policy::Msg),
    ListPolicy(list_policy::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Take(msg) => {
            take::update(msg, &mut model.take, &mut orders.proxy(Msg::Take));
        }
        Msg::List(msg) => {
            list::update(msg, &mut model.list, &mut orders.proxy(Msg::List));
        }
        Msg::CreatePolicy(msg) => {
            create_policy::update(msg, &mut model.create_policy, &mut orders.proxy(Msg::CreatePolicy));
        }
        Msg::ListPolicy(msg) => {
            list_policy::update(msg, &mut model.list_policy, &mut orders.proxy(Msg::ListPolicy));
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
        if cache.snapshot_policy.is_empty() {
            empty![]
        } else {
            list_policy::view(&model.list_policy, cache, session)
                .map_msg(Msg::ListPolicy)
                .merge_attrs(class![C.my_6])
        },
        create_policy_btn(session),
        create_policy::view(&model.create_policy).map_msg(Msg::CreatePolicy),
        list::view(&model.list, cache).map_msg(Msg::List)
    ]
}

fn create_policy_btn(session: Option<&Session>) -> Node<Msg> {
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
            "Create Automatic Snapshot Policy",
            simple_ev(Ev::Click, create_policy::Msg::Open).map_msg(Msg::CreatePolicy)
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
