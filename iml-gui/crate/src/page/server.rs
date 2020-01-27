use crate::{
    components::{alert_indicator, lnet_status, paging, table, Placement},
    extract_api,
    generated::css_classes::C,
    GMsg, MergeAttrs, Route,
};
use iml_wire_types::{warp_drive::Cache, Host, Label};
use seed::{prelude::*, *};
use std::cmp::Ordering;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortField {
    Label,
    Profile,
}

impl Default for SortField {
    fn default() -> Self {
        SortField::Label
    }
}

#[derive(Default)]
pub struct Model {
    hosts: Vec<Host>,
    pager: paging::Model,
    sort: (SortField, paging::Dir),
}

#[derive(Clone)]
pub enum Msg {
    SetHosts(Vec<Host>),
    Page(paging::Msg),
    Sort,
    SortBy(SortField),
    WindowClick,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
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
        }
        Msg::SetHosts(hosts) => {
            model.hosts = hosts;

            orders
                .proxy(Msg::Page)
                .send_msg(paging::Msg::SetTotal(model.hosts.len()));

            orders.send_msg(Msg::Sort);
        }
        Msg::Page(msg) => {
            paging::update(msg, &mut model.pager);
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

fn lnet_by_server<T>(x: &Host, cache: &Cache) -> Option<Vec<Node<T>>> {
    let id = extract_api(&x.lnet_configuration)?;

    let id = id.parse::<u32>().unwrap();

    let config = cache.lnet_configuration.get(&id)?;

    Some(vec![
        lnet_status::view(config).merge_attrs(class![C.mr_1]),
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

pub fn view(cache: &Cache, model: &Model) -> impl View<Msg> {
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
                        tr![
                            table::td_view(vec![
                                a![
                                    class![C.text_blue_500, C.hover__underline, C.mr_2],
                                    attrs! {
                                        At::Href => Route::ServerDetail(x.id.into()).to_href()
                                    },
                                    x.label()
                                ],
                                alert_indicator(&cache.active_alert, &x.resource_uri, true, Placement::Top)
                            ])
                            .merge_attrs(class![C.text_center]),
                            table::td_view(span![timeago(x).unwrap_or_else(|| "".into())])
                                .merge_attrs(class![C.text_center]),
                            table::td_view(span![x.server_profile.ui_name]).merge_attrs(class![C.text_center]),
                            table::td_view(div![lnet_by_server(x, cache).unwrap_or_else(|| vec![])])
                                .merge_attrs(class![C.text_center])
                        ]
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
