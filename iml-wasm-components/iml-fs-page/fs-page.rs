// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use cfg_if::cfg_if;
use iml_action_dropdown::{deferred_action_dropdown as dad, has_lock};
use iml_alert_indicator::{alert_indicator, AlertIndicatorPopoverState};
use iml_environment::ui_root;
use iml_lock_indicator::{lock_indicator, LockIndicatorState};
use iml_pie_chart::pie_chart;
use iml_utils::{extract_api, format_bytes, Locks, WatchState};
use iml_wire_types::{Alert, Filesystem, Target, TargetConfParam, ToCompositeId};
use seed::{a, attrs, class, div, h1, h4, i, prelude::*, span, table, tbody, td, th, thead, tr};
use std::collections::{HashMap, HashSet};
use wasm_bindgen::JsValue;
use web_sys::Element;

cfg_if! {
    if #[cfg(feature = "console_log")] {
        fn init_log() {
            use log::Level;
            match console_log::init_with_level(Level::Trace) {
                Ok(_) => (),
                Err(e) => log::info!("{:?}", e)
            };
        }
    } else {
        fn init_log() {}
    }
}

pub struct Row {
    pub fs: Filesystem,
    pub dropdown: dad::Model,
    pub alert_indicator: WatchState,
    pub lock_indicator: WatchState,
}

type Rows = HashMap<u32, Row>;

#[derive(Default)]
struct Model {
    pub destroyed: bool,
    pub alerts: Vec<Alert>,
    pub rows: Rows,
    pub targets: HashMap<u32, Target<TargetConfParam>>,
    pub locks: Locks,
}

impl Model {
    fn has_fs(&self) -> bool {
        !self.rows.is_empty()
    }
    fn get_mgt(&self, fs: &Filesystem) -> Option<&Target<TargetConfParam>> {
        self.targets
            .values()
            .find(|x| x.kind == "MGT" && fs.mgt == x.resource_uri)
    }
}

#[derive(Clone)]
enum Msg {
    Destroy,
    WindowClick,
    Filesystems(HashMap<u32, Filesystem>),
    FsRowPopoverState(AlertIndicatorPopoverState),
    FsRowLockIndicatorState(LockIndicatorState),
    Targets(HashMap<u32, Target<TargetConfParam>>),
    Alerts(Vec<Alert>),
    SetLocks(Locks),
    ActionDropdown(dad::IdMsg<Filesystem>),
}

fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::Destroy => {
            model.destroyed = true;

            for (id, row) in &mut model.rows {
                *orders = call_update(
                    dad::update,
                    dad::IdMsg(*id, dad::Msg::Destroy),
                    &mut row.dropdown,
                )
                .map_message(Msg::ActionDropdown);
            }
        }
        Msg::WindowClick => {
            for row in &mut model.rows.values_mut() {
                if row.alert_indicator.should_update() {
                    row.alert_indicator.update()
                }

                if row.dropdown.watching.should_update() {
                    row.dropdown.watching.update()
                }

                if row.lock_indicator.should_update() {
                    row.lock_indicator.update()
                }
            }
        }
        Msg::Filesystems(mut filesystems) => {
            let old_keys = model.rows.keys().cloned().collect::<HashSet<u32>>();
            let new_keys = filesystems.keys().cloned().collect::<HashSet<u32>>();

            let to_remove = old_keys.difference(&new_keys);
            let to_add = new_keys.difference(&old_keys);
            let to_change = new_keys.intersection(&old_keys);

            log::info!("old keys {:?}, new keys {:?}", old_keys, new_keys);

            for x in to_remove {
                model.rows.remove(x);
            }

            for x in to_add {
                let fs = filesystems.remove(&x).unwrap();

                model.rows.insert(
                    *x,
                    Row {
                        dropdown: dad::Model {
                            composite_ids: vec![fs.composite_id()],
                            ..dad::Model::default()
                        },
                        alert_indicator: WatchState::Close,
                        lock_indicator: WatchState::Close,
                        fs,
                    },
                );
            }

            for x in to_change {
                let mut r = model.rows.get_mut(&x).unwrap();

                r.fs = filesystems.remove(&x).unwrap();
            }
        }
        Msg::Targets(targets) => {
            model.targets = targets;
        }
        Msg::Alerts(alerts) => {
            model.alerts = alerts;
        }
        Msg::FsRowPopoverState(AlertIndicatorPopoverState((id, state))) => {
            if let Some(x) = model.rows.get_mut(&id) {
                x.alert_indicator = state;
            }
        }
        Msg::FsRowLockIndicatorState(LockIndicatorState(id, state)) => {
            if let Some(x) = model.rows.get_mut(&id) {
                x.lock_indicator = state;
            }
        }
        Msg::SetLocks(locks) => {
            for row in &mut model.rows.values_mut() {
                if has_lock(&locks, &row.fs) {
                    row.dropdown.is_locked = true;
                } else {
                    row.dropdown.is_locked = false;
                }
            }

            model.locks = locks;
        }
        Msg::ActionDropdown(dad::IdMsg(id, msg)) => {
            if let Some(x) = model.rows.get_mut(&id) {
                *orders = call_update(dad::update, dad::IdMsg(id, msg), &mut x.dropdown)
                    .map_message(Msg::ActionDropdown);
            }
        }
    }
}

fn no_fs() -> El<Msg> {
    div![
        class!["no-fs", "well", "text-center"],
        h1!["No File Systems are configured"],
        a![
            class!["btn", "btn-success", "btn-lg"],
            attrs! { At::Href => format!("{}configure/filesystem/create/", ui_root()), At::Type => "button"},
            i![class!["fa", "fa-plus-circle"]],
            "Create File System"
        ]
    ]
}

fn link(href: &str, content: &str) -> El<Msg> {
    a![attrs! { At::Href => href, At::Type => "button" }, content]
}

fn space_usage(used: Option<f64>, total: Option<f64>) -> El<Msg> {
    div![match (used, total) {
        (Some(used), Some(total)) => div![
            pie_chart(used, total, "#aec7e8", "#1f77b4")
                .add_style("width".into(), px(18))
                .add_style("height".into(), px(18))
                .add_style("vertical-align".into(), "bottom".into())
                .add_style("margin-right".into(), px(3)),
            format_bytes(used, Some(1)),
            " / ",
            format_bytes(total, Some(1)),
        ],
        _ => span!["Calculating..."],
    }]
}

fn fs_rows(model: &Model) -> Vec<El<Msg>> {
    model
        .rows
        .values()
        .map(|x| {
            let fs = &x.fs;

            let mgt = model.get_mgt(&fs);

            tr![
                td![link(
                    &format!("{}configure/filesystem/{}", ui_root(), fs.id),
                    &fs.name
                )],
                td![
                    lock_indicator(
                        fs.id,
                        x.lock_indicator.is_open(),
                        fs.composite_id(),
                        &model.locks
                    )
                    .add_style("margin-right".into(), px(5))
                    .map_message(Msg::FsRowLockIndicatorState),
                    alert_indicator(
                        &model.alerts,
                        fs.id,
                        &fs.resource_uri,
                        x.alert_indicator.is_open()
                    )
                    .map_message(Msg::FsRowPopoverState)
                ],
                td![match mgt {
                    Some(mgt) => link(
                        &format!(
                            "{}configure/server/{}",
                            ui_root(),
                            extract_api(&mgt.primary_server).unwrap()
                        ),
                        &mgt.primary_server_name
                    ),
                    None => span!["---"],
                }],
                td![fs.mdts.len().to_string()],
                td![fs.client_count.round().to_string()],
                td![space_usage(
                    Some(fs.bytes_total.unwrap() - fs.bytes_free.unwrap()),
                    fs.bytes_total
                )],
                td![dad::render(fs.id, &x.dropdown, fs).map_message(Msg::ActionDropdown)],
            ]
        })
        .collect()
}

fn view(model: &Model) -> El<Msg> {
    div![
        class!["file-systems"],
        if model.has_fs() {
            div![
                h4![class!["section-header"], "File Systems"],
                table![
                    class!["table"],
                    thead![tr![
                        th!["File System"],
                        th!["Status"],
                        th!["Primary MGS"],
                        th!["Metadata Target Count"],
                        th!["Connected Clients"],
                        th!["Space Used / Total"],
                        th!["Actions"]
                    ]],
                    tbody![fs_rows(&model)]
                ]
            ]
        } else {
            no_fs()
        }
    ]
}

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed {
        return vec![];
    }

    vec![simple_ev(Ev::Click, Msg::WindowClick)]
}

#[wasm_bindgen]
pub struct FsPageCallbacks {
    app: seed::App<Msg, Model, El<Msg>>,
}

#[wasm_bindgen]
impl FsPageCallbacks {
    pub fn destroy(&self) {
        self.app.update(Msg::Destroy);
    }
    pub fn set_filesystems(&self, filesystems: JsValue) {
        self.app
            .update(Msg::Filesystems(filesystems.into_serde().unwrap()));
    }
    pub fn set_targets(&self, targets: JsValue) {
        self.app.update(Msg::Targets(targets.into_serde().unwrap()))
    }
    pub fn set_alerts(&self, alerts: JsValue) {
        self.app.update(Msg::Alerts(alerts.into_serde().unwrap()))
    }
    pub fn set_locks(&self, locks: JsValue) {
        let locks: Locks = locks.into_serde().unwrap();
        self.app.update(Msg::SetLocks(locks));
    }
}

#[wasm_bindgen]
pub fn render_fs_page(el: Element) -> FsPageCallbacks {
    init_log();

    let app = seed::App::build(Model::default(), update, view)
        .mount(el)
        .window_events(window_events)
        .finish()
        .run();

    FsPageCallbacks { app: app.clone() }
}
