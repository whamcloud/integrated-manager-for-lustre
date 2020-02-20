use super::filesystem;
use crate::{
    components::{action_dropdown, alert_indicator, lock_indicator, table as T, Placement},
    extensions::MergeAttrs,
    generated::css_classes::C,
    route::RouteId,
    GMsg, Route,
};
use iml_wire_types::{
    warp_drive::{ArcCache, ArcValuesExt, Locks},
    Filesystem, ToCompositeId,
};
use seed::{prelude::*, *};
use std::collections::HashMap;

struct Row {
    dropdown: action_dropdown::Model,
}

#[derive(Default)]
pub struct Model {
    filesystems: Vec<Filesystem>,
    rows: HashMap<u32, Row>,
}

#[derive(Clone)]
pub enum Msg {
    ActionDropdown(Box<action_dropdown::IdMsg>),
    SetFilesystems(Vec<Filesystem>), // @FIXME: This should be more granular so row state isn't lost.
    WindowClick,
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetFilesystems(cache.filesystem.arc_values().cloned().collect()));
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
        Msg::WindowClick => {
            for (_, r) in model.rows.iter_mut() {
                if r.dropdown.watching.should_update() {
                    r.dropdown.watching.update();
                }
            }
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
            class![C.bg_white, C.border_t, C.border_b, C.border, C.rounded_lg, C.shadow],
            div![
                class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
                h3![class![C.py_4, C.font_normal, C.text_lg], "Filesystems"]
            ],
            T::wrapper_view(vec![
                T::thead_view(vec![
                    T::th_view(plain!["Filesystem"]),
                    T::th_view(plain!["Primary MGS"]),
                    T::th_view(plain!["MDT Count"]),
                    T::th_view(plain!["Connected Clients"]),
                    T::th_view(plain!["Space Used / Total"]),
                ]),
                tbody![model.filesystems.iter().map(|f| match model.rows.get(&f.id) {
                    None => empty![],
                    Some(row) => tr![
                        T::td_view(vec![
                            fs_link(f),
                            lock_indicator::view(all_locks, f).merge_attrs(class![C.mr_2]),
                            alert_indicator(&cache.active_alert, f, true, Placement::Right)
                        ])
                        .merge_attrs(class![C.text_center]),
                        T::td_view(filesystem::mgs(&cache.target.arc_values().cloned().collect(), f))
                            .merge_attrs(class![C.text_center]),
                        T::td_right(plain![f.mdts.len().to_string()]).merge_attrs(class![C.text_center]),
                        T::td_right(filesystem::clients_view(f)),
                        T::td_view(filesystem::size_view(f)).merge_attrs(class![C.text_center]),
                        td![
                            class![C.p_3, C.text_center],
                            action_dropdown::view(f.id, &row.dropdown, all_locks)
                                .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
                        ]
                    ],
                })],
            ])
            .merge_attrs(class![C.pb_2]),
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
