// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{action_dropdown, alert_indicator, lock_indicator, panel, resource_links, Placement},
    extensions::MergeAttrs as _,
    generated::css_classes::C,
    get_target_from_managed_target,
    page::filesystem::standby_hosts_view,
    GMsg,
};
use iml_wire_types::{
    warp_drive::{ArcCache, Locks},
    Session, Target, TargetConfParam, ToCompositeId,
};
use seed::{prelude::*, *};
use std::{borrow::Cow, sync::Arc};

pub struct Model {
    pub target: Arc<Target<TargetConfParam>>,
    dropdown: action_dropdown::Model,
}

impl Model {
    pub fn new(target: Arc<Target<TargetConfParam>>) -> Self {
        Self {
            dropdown: action_dropdown::Model::new(vec![target.composite_id()]),
            target,
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    ActionDropdown(action_dropdown::IdMsg),
    UpdateTarget(Arc<Target<TargetConfParam>>),
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ActionDropdown(x) => {
            let action_dropdown::IdMsg(y, msg) = x;

            action_dropdown::update(
                action_dropdown::IdMsg(y, msg),
                cache,
                &mut model.dropdown,
                &mut orders.proxy(Msg::ActionDropdown),
            );
        }
        Msg::UpdateTarget(x) => {
            if x.id == model.target.id {
                model.target = x;
            }
        }
    }
}

pub fn view(cache: &ArcCache, model: &Model, all_locks: &Locks, session: Option<&Session>) -> Node<Msg> {
    let t = get_target_from_managed_target(cache, &model.target);

    let active_host = t
        .as_ref()
        .and_then(|x| x.active_host_id)
        .and_then(|x| cache.host.get(&x));

    let dev_path = t
        .as_ref()
        .and_then(|x| x.dev_path.as_ref())
        .map(|x| Cow::from(x.to_string()))
        .unwrap_or_else(|| Cow::from("---"));

    panel::view(
        h3![
            class![C.py_4, C.font_normal, C.text_lg],
            &format!("Target: {}", model.target.name),
            lock_indicator::view(all_locks, &model.target).merge_attrs(class![C.ml_2]),
            alert_indicator(&cache.active_alert, &model.target, true, Placement::Right).merge_attrs(class![C.ml_2]),
        ],
        div![
            class![C.grid, C.grid_cols_2, C.gap_4],
            div![class![C.p_6], "Active Server"],
            div![
                class![C.p_6],
                resource_links::server_link(
                    active_host.as_ref().map(|x| &x.resource_uri),
                    &active_host.as_ref().map(|x| x.fqdn.to_string()).unwrap_or_default()
                )
            ],
            div![class![C.p_6], "Standby Servers"],
            div![
                class![C.p_6],
                match t {
                    Some(t) => {
                        standby_hosts_view(cache, &t)
                    }
                    None => {
                        plain!["---"]
                    }
                }
            ],
            div![class![C.p_6], "Device Path"],
            div![class![C.p_6], dev_path],
            action_dropdown::view(model.target.id, &model.dropdown, all_locks, session)
                .merge_attrs(class![C.p_6, C.grid, C.col_span_2])
                .map_msg(Msg::ActionDropdown)
        ],
    )
}
