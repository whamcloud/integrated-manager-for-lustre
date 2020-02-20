use crate::{
    components::{action_dropdown, alert_indicator, lnet_status, lock_indicator, paging, table, Placement},
    extract_id,
    generated::css_classes::C,
    GMsg, MergeAttrs, Route,
};
use iml_wire_types::{
    db::LnetConfigurationRecord,
    warp_drive::{ArcCache, ArcValuesExt, Locks},
    Host, Label, ToCompositeId,
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
    hosts: Vec<Host>,
    rows: HashMap<u32, Row>,
    pager: paging::Model,
    sort: (SortField, paging::Dir),
}

#[derive(Clone)]
pub enum Msg {
    SetHosts(Vec<Host>, im::HashMap<u32, Arc<LnetConfigurationRecord>>), // @FIXME: This should be more granular so row state isn't lost.
    Page(paging::Msg),
    Sort,
    SortBy(SortField),
    WindowClick,
    ActionDropdown(Box<action_dropdown::IdMsg>),
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetHosts(
        cache.host.arc_values().cloned().collect(),
        cache.lnet_configuration.clone(),
    ));
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SortBy(x) => {
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
                    Box::new(|a: &Host, b: &Host| natord::compare(a.label(), b.label()))
                        as Box<dyn FnMut(&Host, &Host) -> Ordering>
                }
                (SortField::Label, paging::Dir::Desc) => {
                    Box::new(|a: &Host, b: &Host| natord::compare(b.label(), a.label()))
                }
                (SortField::Profile, paging::Dir::Asc) => {
                    Box::new(|a: &Host, b: &Host| natord::compare(&a.server_profile.ui_name, &b.server_profile.ui_name))
                }
                (SortField::Profile, paging::Dir::Desc) => {
                    Box::new(|a: &Host, b: &Host| natord::compare(&b.server_profile.ui_name, &a.server_profile.ui_name))
                }
            };

            model.hosts.sort_by(sort_fn);
        }
        Msg::WindowClick => {
            if model.pager.dropdown.should_update() {
                model.pager.dropdown.update();
            }

            for (_, r) in model.rows.iter_mut() {
                if r.dropdown.watching.should_update() {
                    r.dropdown.watching.update();
                }
            }
        }
        Msg::SetHosts(hosts, lnet_configs) => {
            model.hosts = hosts;

            model.rows = model
                .hosts
                .iter()
                .map(|x| {
                    let mut config = lnet_by_server(x, &lnet_configs)
                        .map(|x| vec![x.composite_id()])
                        .unwrap_or_default();

                    let mut actions = vec![x.composite_id()];

                    actions.append(&mut config);

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
            paging::update(msg, &mut model.pager);
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

fn sort_header(label: &str, sort_field: SortField, model: &Model) -> Node<Msg> {
    let is_active = model.sort.0 == sort_field;

    let table_cls = class![C.text_center];

    let table_cls = if is_active {
        table_cls.merge_attrs(table::th_sortable_cls())
    } else {
        table_cls
    };

    table::th_view(a![
        class![C.select_none, C.cursor_pointer, C.font_semibold],
        mouse_ev(Ev::Click, move |_| Msg::SortBy(sort_field)),
        label,
        if is_active {
            paging::dir_toggle_view(model.sort.1, class![C.w_5, C.h_4, C.inline, C.ml_1, C.text_blue_500])
        } else {
            empty![]
        }
    ])
    .merge_attrs(table_cls)
}

fn lnet_by_server(
    x: &Host,
    lnet_configs: &im::HashMap<u32, Arc<LnetConfigurationRecord>>,
) -> Option<Arc<LnetConfigurationRecord>> {
    let id = extract_id(&x.lnet_configuration)?;

    let id = id.parse::<u32>().unwrap();

    lnet_configs.get(&id).cloned()
}

pub fn view(cache: &ArcCache, model: &Model, all_locks: &Locks) -> impl View<Msg> {
    div![
        class![C.bg_white, C.border_t, C.border_b, C.border, C.rounded_lg, C.shadow],
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
                        sort_header("Host", SortField::Label, model),
                        table::th_view(Node::new_text("Boot time")).merge_attrs(class![C.text_center]),
                        sort_header("Profile", SortField::Profile, model),
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
                                    alert_indicator(&cache.active_alert, &x.resource_uri, true, Placement::Top)
                                ])
                                .merge_attrs(class![C.text_center]),
                                table::td_view(span![timeago(x).unwrap_or_else(|| "".into())])
                                    .merge_attrs(class![C.text_center]),
                                table::td_view(span![x.server_profile.ui_name]).merge_attrs(class![C.text_center]),
                                table::td_view(
                                    div![lnet_by_server_view(x, cache, all_locks).unwrap_or_else(|| vec![])]
                                )
                                .merge_attrs(class![C.text_center]),
                                td![
                                    class![C.p_3, C.text_center],
                                    action_dropdown::view(x.id, &row.dropdown, all_locks)
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
    let config = lnet_by_server(x, &cache.lnet_configuration)?;

    Some(nodes![
        lnet_status::view(&config, all_locks).merge_attrs(class![C.mr_2]),
        alert_indicator(
            &cache.active_alert,
            &format!("/api/lnet_configuration/{}/", config.id),
            true,
            Placement::Top,
        ),
    ])
}

fn timeago(x: &Host) -> Option<String> {
    let boot_time = x.boot_time.as_ref()?;

    let dt = chrono::DateTime::parse_from_rfc3339(&format!("{}-00:00", boot_time)).unwrap();

    Some(format!("{}", chrono_humanize::HumanTime::from(dt)))
}
