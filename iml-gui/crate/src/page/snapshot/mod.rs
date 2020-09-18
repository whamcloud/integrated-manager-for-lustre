// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod list;
mod list_interval;
mod take;

use crate::{
    components::{
        attrs, font_awesome, font_awesome_outline, form, paging, panel, resource_links, table, tooltip, Placement,
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
    Filesystem,
};
use seed::{prelude::*, *};
use std::{cmp::Ordering, ops::Deref, sync::Arc};

#[derive(Default, Debug)]
pub struct Model {
    take: take::Model,
    list_interval: list_interval::Model,
    list: list::Model,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, record: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list
            .update_record(record.clone(), cache, &mut orders.proxy(Msg::List));

        self.list_interval
            .update_record(record, cache, &mut orders.proxy(Msg::ListInterval));
    }
    fn remove_record(&mut self, record: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list.remove_record(record, cache, &mut orders.proxy(Msg::List));

        self.list_interval
            .remove_record(record, cache, &mut orders.proxy(Msg::ListInterval));
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.list.set_records(cache, &mut orders.proxy(Msg::List));

        self.list_interval
            .set_records(cache, &mut orders.proxy(Msg::ListInterval));
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Take(take::Msg),
    ListInterval(list_interval::Msg),
    List(list::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Take(msg) => {
            take::update(msg, &mut model.take, &mut orders.proxy(Msg::Take));
        }
        Msg::ListInterval(msg) => {
            list_interval::update(msg, &mut model.list_interval, &mut orders.proxy(Msg::ListInterval));
        }
        Msg::List(msg) => {
            list::update(msg, &mut model.list, &mut orders.proxy(Msg::List));
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
        take::view(&model.take, &fs_names)
            .map_msg(Msg::Take)
            .merge_attrs(class![C.my_6]),
        list_interval::view(&model.list_interval, cache)
            .map_msg(Msg::ListInterval)
            .merge_attrs(class![C.my_6]),
        list::view(&model.list, cache).map_msg(Msg::List)
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
