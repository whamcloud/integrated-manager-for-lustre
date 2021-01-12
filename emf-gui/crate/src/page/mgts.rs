// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{action_dropdown, alert_indicator, lock_indicator, resource_links, table, Placement},
    extensions::MergeAttrs,
    generated::css_classes::C,
    get_target_from_managed_target,
    page::filesystem::standby_hosts_view,
    route::RouteId,
    GMsg, Route,
};
use emf_api_utils::extract_id;
use emf_wire_types::{
    db::{ManagedTargetRecord, TargetKind},
    warp_drive::{ArcCache, ArcValuesExt, Locks},
    Label, Session, ToCompositeId,
};
use seed::{prelude::*, *};
use std::{borrow::Cow, collections::HashMap, sync::Arc};

pub struct Row {
    dropdown: action_dropdown::Model,
}

#[derive(Default)]
pub struct Model {
    pub rows: HashMap<i32, Row>,
    pub mgts: Vec<Arc<ManagedTargetRecord>>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    ActionDropdown(Box<action_dropdown::IdMsg>),
    SetTargets(Vec<Arc<ManagedTargetRecord>>),
    RemoveTarget(i32),
    AddTarget(Arc<ManagedTargetRecord>),
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetTargets(cache.target.values().cloned().collect()));
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ActionDropdown(x) => {
            let action_dropdown::IdMsg(id, msg) = *x;

            if let Some(x) = model.rows.get_mut(&id) {
                action_dropdown::update(
                    action_dropdown::IdMsg(id, msg),
                    cache,
                    &mut x.dropdown,
                    &mut orders.proxy(|x| Msg::ActionDropdown(Box::new(x))),
                );
            }
        }
        Msg::SetTargets(xs) => {
            model.rows = xs
                .iter()
                .map(|x| {
                    (
                        x.id,
                        Row {
                            dropdown: action_dropdown::Model::new(vec![x.composite_id()]),
                        },
                    )
                })
                .collect();

            let mut mgts: Vec<_> = xs.into_iter().filter(|x| x.get_kind() == TargetKind::Mgt).collect();

            mgts.sort_by(|a, b| natord::compare(a.label(), b.label()));

            model.mgts = mgts;
        }
        Msg::RemoveTarget(id) => {
            model.mgts.retain(|x| x.id != id);
            model.rows.remove(&id);
        }
        Msg::AddTarget(x) => match model.mgts.iter().position(|y| y.id == x.id) {
            Some(p) => {
                model.mgts.remove(p);
                model.mgts.insert(p, x);
            }
            None => {
                model.rows.insert(
                    x.id,
                    Row {
                        dropdown: action_dropdown::Model::new(vec![x.composite_id()]),
                    },
                );
            }
        },
    }
}

pub fn view(cache: &ArcCache, model: &Model, all_locks: &Locks, session: Option<&Session>) -> Node<Msg> {
    div![
        class![C.bg_white],
        div![
            class![C.px_6, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "MGTs"]
        ],
        if model.mgts.is_empty() {
            div![
                class![C.text_3xl, C.text_center],
                h1![class![C.m_2, C.text_gray_600], "No MGTs found"],
            ]
        } else {
            table::wrapper_view(vec![
                table::thead_view(vec![
                    table::th_view(plain!["Name"]),
                    table::th_view(plain!["Filesystems"]),
                    table::th_view(plain!["Device Path"]),
                    table::th_view(plain!["Active Server"]),
                    table::th_view(plain!["Standby Servers"]),
                    th![],
                ]),
                tbody![model.mgts.iter().map(|x| match model.rows.get(&x.id) {
                    None => empty![],
                    Some(row) => {
                        let fs: Vec<_> = cache
                            .filesystem
                            .arc_values()
                            .filter(|y| {
                                extract_id(&y.mgt)
                                    .and_then(|y| y.parse::<i32>().ok())
                                    .filter(|y| y == &x.id)
                                    .is_some()
                            })
                            .collect();

                        let t = get_target_from_managed_target(cache, x);

                        let active_host = t.and_then(|x| x.active_host_id).and_then(|x| cache.host.get(&x));

                        let dev_path = t
                            .and_then(|x| x.dev_path.as_ref())
                            .map(|x| Cow::from(x.to_string()))
                            .unwrap_or_else(|| Cow::from("---"));

                        tr![
                            table::td_center(vec![
                                a![
                                    class![C.text_blue_500, C.hover__underline],
                                    attrs! {At::Href => Route::Target(RouteId::from(x.id)).to_href()},
                                    &x.label()
                                ],
                                lock_indicator::view(all_locks, &x).merge_attrs(class![C.ml_2]),
                                alert_indicator(&cache.active_alert, &x, true, Placement::Right)
                                    .merge_attrs(class![C.ml_2]),
                            ]),
                            table::td_center(fs.into_iter().map(resource_links::fs_link).collect::<Vec<_>>()),
                            table::td_center(plain![dev_path]),
                            table::td_center(resource_links::server_link(
                                active_host.map(|x| &x.resource_uri),
                                active_host.map(|x| x.fqdn.to_string()).as_deref().unwrap_or_default(),
                            )),
                            table::td_center(match t {
                                Some(t) => {
                                    standby_hosts_view(cache, &t)
                                }
                                None => {
                                    plain!["---"]
                                }
                            }),
                            td![
                                class![C.p_3, C.text_center],
                                action_dropdown::view(x.id, &row.dropdown, all_locks, session)
                                    .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
                            ]
                        ]
                    }
                })],
            ])
        }
    ]
}
