use crate::{
    components::{action_dropdown, alert_indicator, lock_indicator, paging, table as t, Placement},
    extensions::MergeAttrs,
    generated::css_classes::C,
    page::filesystem,
    route::RouteId,
    GMsg, Route,
};
use iml_wire_types::{
    warp_drive::{ArcCache, Locks},
    Filesystem, ToCompositeId,
};
use seed::{prelude::*, *};
use std::{collections::HashMap, sync::Arc};

struct Row {
    dropdown: action_dropdown::Model,
}

#[derive(Default)]
pub struct Model {
    filesystems: Vec<Arc<Filesystem>>,
    pager: paging::Model,
    rows: HashMap<u32, Row>,
}

#[derive(Clone)]
pub enum Msg {
    ActionDropdown(Box<action_dropdown::IdMsg>),
    AddFilesystem(Arc<Filesystem>),
    Page(paging::Msg),
    RemoveFilesystem(u32),
    SetFilesystems(Vec<Arc<Filesystem>>),
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetFilesystems(cache.filesystem.values().cloned().collect()));
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
        Msg::SetFilesystems(filesystems) => {
            model.filesystems = filesystems;

            orders
                .proxy(Msg::Page)
                .send_msg(paging::Msg::SetTotal(model.filesystems.len()));

            model.rows = model
                .filesystems
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
        }
        Msg::Page(msg) => {
            paging::update(msg, &mut model.pager, &mut orders.proxy(Msg::Page));
        }
        Msg::AddFilesystem(fs) => {
            match model.filesystems.iter().position(|x| x.id == fs.id) {
                Some(p) => {
                    model.filesystems.remove(p);
                    model.filesystems.insert(p, fs);
                }
                None => {
                    model.rows.insert(
                        fs.id,
                        Row {
                            dropdown: action_dropdown::Model::new(vec![fs.composite_id()]),
                        },
                    );

                    model.filesystems.push(fs);
                }
            };

            orders
                .proxy(Msg::Page)
                .send_msg(paging::Msg::SetTotal(model.filesystems.len()));
        }
        Msg::RemoveFilesystem(id) => {
            model.rows.remove(&id);

            model.filesystems.retain(|x| x.id != id);

            orders
                .proxy(Msg::Page)
                .send_msg(paging::Msg::SetTotal(model.filesystems.len()));
        }
    }
}

pub fn view(cache: &ArcCache, model: &Model, all_locks: &Locks) -> impl View<Msg> {
    if cache.filesystem.is_empty() {
        div![
            class![C.text_3xl, C.text_center],
            h1![class![C.m_2, C.text_gray_600], "No filesystems found"],
        ]
    } else {
        div![
            class![C.bg_white, C.rounded_lg],
            div![
                class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
                h3![class![C.py_4, C.font_normal, C.text_lg], "Filesystems"]
            ],
            t::wrapper_view(vec![
                t::thead_view(vec![
                    t::th_view(plain!["Filesystem"]),
                    t::th_view(plain!["Primary MGS"]),
                    t::th_view(plain!["MDT Count"]),
                    t::th_view(plain!["Connected Clients"]),
                    t::th_view(plain!["Space Used / Total"]),
                ]),
                tbody![model.filesystems[model.pager.range()]
                    .iter()
                    .map(|f| match model.rows.get(&f.id) {
                        None => empty![],
                        Some(row) => {
                            let xs: Vec<_> = cache.target.values().cloned().collect();

                            tr![
                                t::td_view(vec![
                                    fs_link(f),
                                    lock_indicator::view(all_locks, f).merge_attrs(class![C.mr_2]),
                                    alert_indicator(&cache.active_alert, f, true, Placement::Right)
                                ])
                                .merge_attrs(class![C.text_center]),
                                t::td_center(filesystem::mgs(&xs, f)),
                                t::td_center(plain![f.mdts.len().to_string()]),
                                t::td_center(filesystem::clients_view(f)),
                                t::td_center(filesystem::size_view(f)),
                                td![
                                    class![C.p_3, C.text_center],
                                    action_dropdown::view(f.id, &row.dropdown, all_locks)
                                        .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
                                ]
                            ]
                        }
                    })],
            ])
            .merge_attrs(class![C.p_6]),
            div![
                class![C.flex, C.justify_end, C.py_1, C.pr_3],
                paging::limit_selection_view(&model.pager).map_msg(Msg::Page),
                paging::page_count_view(&model.pager),
                paging::next_prev_view(&model.pager).map_msg(Msg::Page)
            ],
        ]
    }
}

fn fs_link<T>(f: &iml_wire_types::Filesystem) -> Node<T> {
    a![
        class![C.text_blue_500, C.hover__underline, C.mr_2],
        attrs! {At::Href => Route::Filesystem(RouteId::from(f.id)).to_href()},
        &f.label
    ]
}
