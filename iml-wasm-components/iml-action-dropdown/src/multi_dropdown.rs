// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    deferred_action_dropdown as dad,
    model::{self, group_actions_by_label, Record, RecordMap},
};
use futures::{future::join_all, Future};
use iml_wire_types::ToCompositeId;
use seed::{fetch::FetchObject, prelude::*, Request};

pub fn fetch_urls(urls: Vec<String>) -> impl Future<Item = Msg, Error = Msg> {
    let futs = urls
        .into_iter()
        .map(|url| Request::new(url).fetch_json(std::convert::identity));

    join_all(futs)
        .map(Msg::UrlsFetched)
        .map_err(|x| Msg::UrlsFetched(vec![x]))
}

#[derive(Default)]
pub struct Model {
    pub id: u32,
    pub urls: Vec<String>,
    pub records: RecordMap<Record>,
    pub dropdown: dad::Model,
}

#[derive(Clone)]
pub enum Msg {
    FetchUrls,
    UrlsFetched(Vec<FetchObject<model::Record>>),
    DeferredActionDropdown(dad::IdMsg<model::Record>),
}

pub fn update(msg: Msg, mut model: &mut Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::DeferredActionDropdown(dad::IdMsg(id, msg)) => match msg {
            dad::Msg::StartFetch => {
                model.dropdown.activated = true;
                model.dropdown.first_fetch_activated = true;

                orders.skip().send_msg(Msg::FetchUrls);
            }
            x => {
                *orders = call_update(dad::update, dad::IdMsg(id, x), &mut model.dropdown)
                    .map_message(Msg::DeferredActionDropdown)
            }
        },
        Msg::FetchUrls => {
            let urls = model.urls.drain(..).collect();
            orders.skip().perform_cmd(fetch_urls(urls));
        }
        Msg::UrlsFetched(xs) => {
            model.records = xs
                .into_iter()
                .filter_map(|x| match x.response() {
                    Ok(resp) => Some(resp.data),
                    Err(e) => {
                        orders.send_msg(Msg::DeferredActionDropdown(dad::IdMsg(
                            model.id,
                            dad::Msg::Error(e.into()),
                        )));

                        None
                    }
                })
                .map(model::record_to_map)
                .collect();

            model.dropdown.composite_ids =
                model.records.values().map(|x| x.composite_id()).collect();

            orders
                .skip()
                .send_msg(Msg::DeferredActionDropdown(dad::IdMsg(
                    model.id,
                    dad::Msg::FetchActions,
                )));
        }
    }
}

// View
pub fn view(model: &Model) -> El<Msg> {
    let actions = group_actions_by_label(&model.dropdown.actions, &model.records);

    dad::render_with_action(model.id, &model.dropdown, actions)
        .map_message(Msg::DeferredActionDropdown)
}
