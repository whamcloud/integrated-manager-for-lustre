use crate::{
    components::{action_dropdown, alert_indicator, lock_indicator, resource_links, table, Placement},
    extensions::MergeAttrs,
    extract_id,
    generated::css_classes::C,
    route::RouteId,
    GMsg, Route,
};
use iml_wire_types::{
    warp_drive::{ArcCache, ArcValuesExt, Locks},
    Session, Target, TargetConfParam, TargetKind, ToCompositeId,
};
use seed::{prelude::*, *};
use std::{collections::HashMap, sync::Arc};

pub struct Row {
    dropdown: action_dropdown::Model,
}

#[derive(Default)]
pub struct Model {
    pub rows: HashMap<u32, Row>,
    pub mgts: Vec<Arc<Target<TargetConfParam>>>,
}

#[derive(Clone)]
pub enum Msg {
    ActionDropdown(Box<action_dropdown::IdMsg>),
    SetTargets(Vec<Arc<Target<TargetConfParam>>>),
    RemoveTarget(u32),
    AddTarget(Arc<Target<TargetConfParam>>),
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

            let mut mgts: Vec<_> = xs.into_iter().filter(|x| x.kind == TargetKind::Mgt).collect();

            mgts.sort_by(|a, b| natord::compare(&a.name, &b.name));

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
                    table::th_view(plain!["Volume"]),
                    table::th_view(plain!["Primary Server"]),
                    table::th_view(plain!["Failover Server"]),
                    table::th_view(plain!["Started on"]),
                    th![],
                ]),
                tbody![model.mgts.iter().map(|x| match model.rows.get(&x.id) {
                    None => empty![],
                    Some(row) => {
                        let fs = cache.filesystem.arc_values().filter(|y| {
                            extract_id(&y.mgt)
                                .and_then(|y| y.parse::<u32>().ok())
                                .filter(|y| y == &x.id)
                                .is_some()
                        });

                        tr![
                            table::td_center(vec![
                                a![
                                    class![C.text_blue_500, C.hover__underline],
                                    attrs! {At::Href => Route::Target(RouteId::from(x.id)).to_href()},
                                    &x.name
                                ],
                                lock_indicator::view(all_locks, &x).merge_attrs(class![C.ml_2]),
                                alert_indicator(&cache.active_alert, &x, true, Placement::Right)
                                    .merge_attrs(class![C.ml_2]),
                            ]),
                            table::td_center(fs.map(resource_links::fs_link).collect::<Vec<_>>()),
                            table::td_center(resource_links::volume_link(x)),
                            table::td_center(resource_links::server_link(
                                Some(&x.primary_server),
                                &x.primary_server_name
                            )),
                            table::td_center(resource_links::server_link(
                                x.failover_servers.first(),
                                &x.failover_server_name
                            )),
                            table::td_center(resource_links::server_link(x.active_host.as_ref(), &x.active_host_name)),
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
