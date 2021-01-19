// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{action_dropdown, alert_indicator, date, lnet_status, lock_indicator, paging, table, Placement},
    generated::css_classes::C,
    page::server::date_view,
    GMsg, MergeAttrs, Route,
};
use emf_wire_types::db::CorosyncConfigurationRecord;
use emf_wire_types::{
    db::{LnetConfigurationRecord, PacemakerConfigurationRecord},
    warp_drive::{ArcCache, Locks},
    Host, Label, Session, ToCompositeId,
};
use seed::{prelude::*, *};
use std::{cmp::Ordering, collections::HashMap, sync::Arc};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortField {
    Label,
    Profile,
}

impl Default for SortField {
    fn default() -> Self {
        Self::Label
    }
}

struct Row {
    dropdown: action_dropdown::Model,
}

#[derive(Default)]
pub struct Model {
    hosts: Vec<Arc<Host>>,
    rows: HashMap<i32, Row>,
    pager: paging::Model,
    sort: (SortField, paging::Dir),
}

#[derive(Clone, Debug)]
pub enum Msg {
    SetHosts(
        Vec<Arc<Host>>,
        im::HashMap<i32, Arc<LnetConfigurationRecord>>,
        im::HashMap<i32, Arc<PacemakerConfigurationRecord>>,
        im::HashMap<i32, Arc<CorosyncConfigurationRecord>>,
    ), // @FIXME: This should be more granular so row state isn't lost.
    Page(paging::Msg),
    Sort,
    SortBy(table::SortBy<SortField>),
    ActionDropdown(Box<action_dropdown::IdMsg>),
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetHosts(
        cache.host.values().cloned().collect(),
        cache.lnet_configuration.clone(),
        cache.pacemaker_configuration.clone(),
        cache.corosync_configuration.clone(),
    ));
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
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
        Msg::Sort => {
            let sort_fn = match model.sort {
                (SortField::Label, paging::Dir::Asc) => {
                    Box::new(|a: &Arc<Host>, b: &Arc<Host>| natord::compare(a.label(), b.label()))
                        as Box<dyn FnMut(&Arc<Host>, &Arc<Host>) -> Ordering>
                }
                (SortField::Label, paging::Dir::Desc) => {
                    Box::new(|a: &Arc<Host>, b: &Arc<Host>| natord::compare(b.label(), a.label()))
                }
                (SortField::Profile, paging::Dir::Asc) => Box::new(|a: &Arc<Host>, b: &Arc<Host>| {
                    natord::compare(&a.server_profile.ui_name, &b.server_profile.ui_name)
                }),
                (SortField::Profile, paging::Dir::Desc) => Box::new(|a: &Arc<Host>, b: &Arc<Host>| {
                    natord::compare(&b.server_profile.ui_name, &a.server_profile.ui_name)
                }),
            };

            model.hosts.sort_by(sort_fn);
        }
        Msg::SetHosts(hosts, lnet_configs, pacemaker_configs, corosync_configs) => {
            model.hosts = hosts;

            model.rows = model
                .hosts
                .iter()
                .map(|x| {
                    let xs = x
                        .lnet_id()
                        .and_then(|x| lnet_configs.get(&x))
                        .map(|x| vec![x.composite_id()])
                        .unwrap_or_default();

                    let ys = x
                        .pacemaker_id()
                        .and_then(|x| pacemaker_configs.get(&x))
                        .map(|x| vec![x.composite_id()])
                        .unwrap_or_default();

                    let zs = x
                        .corosync_id()
                        .and_then(|x| corosync_configs.get(&x))
                        .map(|x| vec![x.composite_id()])
                        .unwrap_or_default();

                    let actions = std::iter::once(x.composite_id())
                        .chain(xs)
                        .chain(ys)
                        .chain(zs)
                        .collect();

                    (
                        x.id,
                        Row {
                            dropdown: action_dropdown::Model::new(actions),
                        },
                    )
                })
                .collect();

            orders
                .proxy(Msg::Page)
                .send_msg(paging::Msg::SetTotal(model.hosts.len()));

            orders.send_msg(Msg::Sort);
        }
        Msg::Page(msg) => {
            paging::update(msg, &mut model.pager, &mut orders.proxy(Msg::Page));
        }
        Msg::ActionDropdown(msg) => {
            let action_dropdown::IdMsg(id, msg) = *msg;

            if let Some(x) = model.rows.get_mut(&id) {
                action_dropdown::update(
                    action_dropdown::IdMsg(id, msg),
                    cache,
                    &mut x.dropdown,
                    &mut orders.proxy(|x| Msg::ActionDropdown(Box::new(x))),
                );
            }
        }
    }
}

pub fn view(
    cache: &ArcCache,
    session: Option<&Session>,
    model: &Model,
    all_locks: &Locks,
    sd: &date::Model,
) -> impl View<Msg> {
    div![
        class![C.bg_white],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "Servers"]
        ],
        if cache.host.is_empty() {
            p!["No hosts found"]
        } else {
            div![
                table::wrapper_view(vec![
                    table::thead_view(vec![
                        table::sort_header("Host", SortField::Label, model.sort.0, model.sort.1).map_msg(Msg::SortBy),
                        table::th_view(Node::new_text("Boot time")).merge_attrs(class![C.text_center]),
                        table::sort_header("Profile", SortField::Profile, model.sort.0, model.sort.1)
                            .map_msg(Msg::SortBy),
                        table::th_view(Node::new_text("LNet")).merge_attrs(class![C.text_center]),
                    ]),
                    tbody![model.hosts[model.pager.range()].iter().map(|x| {
                        match model.rows.get(&x.id) {
                            None => empty![],
                            Some(row) => tr![
                                table::td_view(vec![
                                    a![
                                        class![C.text_blue_500, C.hover__underline, C.mr_2],
                                        attrs! {
                                            At::Href => Route::Server(x.id.into()).to_href()
                                        },
                                        x.label()
                                    ],
                                    lock_indicator::view(all_locks, x).merge_attrs(class![C.mr_2]),
                                    alert_indicator(&cache.active_alert, &x, true, Placement::Top)
                                ])
                                .merge_attrs(class![C.text_center]),
                                table::td_view(date_view(sd, &x.boot_time)).merge_attrs(class![C.text_center]),
                                table::td_view(span![x.server_profile.ui_name]).merge_attrs(class![C.text_center]),
                                table::td_view(div![lnet_by_server_view(x, cache, all_locks).unwrap_or_else(Vec::new)])
                                    .merge_attrs(class![C.text_center]),
                                td![
                                    class![C.p_3, C.text_center],
                                    action_dropdown::view(x.id, &row.dropdown, all_locks, session)
                                        .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
                                ]
                            ],
                        }
                    })]
                ])
                .merge_attrs(class![C.my_6]),
                div![
                    class![C.flex, C.justify_end, C.py_1, C.pr_3],
                    paging::limit_selection_view(&model.pager).map_msg(Msg::Page),
                    paging::page_count_view(&model.pager),
                    paging::next_prev_view(&model.pager).map_msg(Msg::Page)
                ],
            ]
        }
    ]
}

fn lnet_by_server_view<T>(x: &Host, cache: &ArcCache, all_locks: &Locks) -> Option<Vec<Node<T>>> {
    let id = x.lnet_id()?;

    let config = cache.lnet_configuration.get(&id)?;

    Some(nodes![
        lnet_status::view(config, all_locks).merge_attrs(class![C.mr_2]),
        alert_indicator(&cache.active_alert, &config, true, Placement::Top,),
    ])
}
