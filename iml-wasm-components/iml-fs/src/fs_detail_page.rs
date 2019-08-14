// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{client_count, file_usage, link, mgt_link, server_link, space_usage};
use bootstrap_components::{bs_button, bs_modal, bs_table, bs_well::well};
use cfg_if::cfg_if;
use iml_action_dropdown::{deferred_action_dropdown as dad, has_lock};
use iml_alert_indicator::{alert_indicator, AlertIndicatorPopoverState};
use iml_environment::ui_root;
use iml_lock_indicator::{lock_indicator, LockIndicatorState};
use iml_paging::{paging, update_paging, Paging, PagingMsg};
use iml_utils::{IntoSerdeOpt as _, Locks, WatchState};
use iml_wire_types::{Alert, Filesystem, Host, Target, TargetConfParam, ToCompositeId};
use seed::{class, div, dom_types::Attrs, h4, h5, i, prelude::*, style, tbody, td, th, thead, tr};
use std::{
    borrow::Cow,
    collections::{HashMap, HashSet},
};
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

#[derive(Default)]
struct TableRow {
    pub alert_indicator: WatchState,
    pub dropdown: dad::Model,
    pub lock_indicator: WatchState,
}

struct FsDetail {
    pub dropdown: dad::Model,
    pub alert_indicator: WatchState,
}

impl Default for FsDetail {
    fn default() -> Self {
        FsDetail {
            alert_indicator: Default::default(),
            dropdown: dad::Model {
                tooltip: iml_tooltip::Model {
                    placement: iml_tooltip::TooltipPlacement::Top,
                    ..Default::default()
                },
                ..Default::default()
            },
        }
    }
}

#[derive(Default)]
struct Model {
    pub destroyed: bool,
    pub alerts: Vec<Alert>,
    pub fs: Option<Filesystem>,
    pub fs_detail: FsDetail,
    pub mdts: Vec<Target<TargetConfParam>>,
    pub mdt_paging: Paging,
    pub mgt: Vec<Target<TargetConfParam>>,
    pub mount_modal_open: bool,
    pub osts: Vec<Target<TargetConfParam>>,
    pub ost_paging: Paging,
    pub table_rows: HashMap<u32, TableRow>,
    pub locks: Locks,
    pub hosts: HashMap<u32, Host>,
    pub stratagem: iml_stratagem::Model,
    pub scan_now: iml_stratagem::scan_now::Model,
    stratagem_ready: bool,
}

impl Model {
    fn stratagem_ready(&self) -> bool {
        !self.mdts.is_empty()
            && !self.hosts.is_empty()
            && self.fs.is_some()
            && self
                .hosts
                .values()
                .filter(|x| {
                    self.mdts
                        .iter()
                        .any(|mdt| mdt.active_host_name == x.address)
                })
                .all(|x| x.server_profile.name == "stratagem_server")
    }
}

#[derive(Clone)]
enum Msg {
    Alerts(Vec<Alert>),
    CloseMountModal,
    Destroy,
    Filesystem(Option<Filesystem>),
    FsDetailDropdown(dad::IdMsg<Filesystem>),
    FsDetailPopoverState(AlertIndicatorPopoverState),
    FsRowDropdown(dad::IdMsg<Target<TargetConfParam>>),
    FsRowIndicatorState(AlertIndicatorPopoverState),
    FsRowLockIndicatorState(LockIndicatorState),
    OstPaging(PagingMsg),
    MdtPaging(PagingMsg),
    Locks(Locks),
    OpenMountModal,
    Targets(HashMap<u32, Target<TargetConfParam>>),
    WindowClick,
    CloseCommandModal,
    Hosts(HashMap<u32, Host>),
    InodeTable(iml_stratagem::Msg),
    StratagemInit(iml_stratagem::Msg),
    StratagemComponent(iml_stratagem::Msg),
    ScanNow(iml_stratagem::scan_now::Msg),
}

fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::Destroy => {
            model.destroyed = true;
        }
        Msg::WindowClick => {
            if model.fs_detail.alert_indicator.should_update() {
                model.fs_detail.alert_indicator.update();
            }

            if model.fs_detail.dropdown.watching.should_update() {
                model.fs_detail.dropdown.watching.update();
            }

            if model.ost_paging.dropdown.should_update() {
                model.ost_paging.dropdown.update();
            }

            if model.mdt_paging.dropdown.should_update() {
                model.mdt_paging.dropdown.update();
            }

            for row in &mut model.table_rows.values_mut() {
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

            if model.stratagem.run_config.watching.should_update() {
                model.stratagem.run_config.watching.update();
            }

            if model.stratagem.report_config.watching.should_update() {
                model.stratagem.report_config.watching.update();
            }

            if model.stratagem.purge_config.watching.should_update() {
                model.stratagem.purge_config.watching.update();
            }

            if model.scan_now.purge_config.watching.should_update() {
                model.scan_now.purge_config.watching.update();
            }

            if model.scan_now.report_config.watching.should_update() {
                model.scan_now.report_config.watching.update();
            }
        }
        Msg::CloseCommandModal => {
            model.stratagem.disabled = false;
        }
        Msg::Filesystem(fs) => {
            if let Some(fs) = &fs {
                model.fs_detail.dropdown.composite_ids = vec![fs.composite_id()];

                model.stratagem.fs_id = fs.id;

                model.stratagem_ready = model.stratagem_ready();
            };

            model.fs = fs;
        }
        Msg::Locks(locks) => {
            if let Some(fs) = &model.fs {
                model.fs_detail.dropdown.is_locked = has_lock(&locks, fs);
            }

            model.locks = locks;
        }
        Msg::Targets(mut targets) => {
            let old_keys = model.table_rows.keys().cloned().collect::<HashSet<u32>>();
            let new_keys = targets.keys().cloned().collect::<HashSet<u32>>();

            let to_remove = old_keys.difference(&new_keys);
            let to_add = new_keys.difference(&old_keys);

            for x in to_remove {
                model.table_rows.remove(x);
            }

            for x in to_add {
                model.table_rows.insert(
                    *x,
                    TableRow {
                        dropdown: dad::Model {
                            composite_ids: vec![targets[x].composite_id()],
                            ..dad::Model::default()
                        },
                        ..TableRow::default()
                    },
                );
            }

            let (mgt, mut mdts, mut osts) = targets.drain().map(|(_, v)| v).fold(
                (vec![], vec![], vec![]),
                |(mut mgt, mut mdts, mut osts), x| {
                    if x.kind == "OST" {
                        osts.push(x);
                    } else if x.kind == "MDT" {
                        mdts.push(x);
                    } else if x.kind == "MGT" {
                        mgt.push(x);
                    }

                    (mgt, mdts, osts)
                },
            );

            model.mgt = mgt;

            mdts.sort_by(|a, b| natord::compare(&a.name, &b.name));
            model.mdt_paging.total = mdts.len();
            model.mdts = mdts;

            osts.sort_by(|a, b| natord::compare(&a.name, &b.name));
            model.ost_paging.total = osts.len();
            model.osts = osts;

            model.stratagem_ready = model.stratagem_ready();
        }
        Msg::OstPaging(msg) => update_paging(msg, &mut model.ost_paging),
        Msg::MdtPaging(msg) => update_paging(msg, &mut model.mdt_paging),
        Msg::Hosts(hosts) => {
            model.hosts = hosts;

            model.stratagem_ready = model.stratagem_ready();
        }
        Msg::Alerts(alerts) => {
            model.alerts = alerts;
        }
        Msg::FsDetailPopoverState(AlertIndicatorPopoverState((_, state))) => {
            model.fs_detail.alert_indicator = state;
        }
        Msg::FsRowIndicatorState(AlertIndicatorPopoverState((id, state))) => {
            if let Some(row) = model.table_rows.get_mut(&id) {
                row.alert_indicator = state;
            }
        }
        Msg::FsRowDropdown(dad::IdMsg(id, msg)) => {
            if let Some(row) = model.table_rows.get_mut(&id) {
                dad::update(
                    dad::IdMsg(id, msg),
                    &mut row.dropdown,
                    &mut orders.proxy(Msg::FsRowDropdown),
                );
            }
        }
        Msg::FsRowLockIndicatorState(LockIndicatorState(id, state)) => {
            if let Some(row) = model.table_rows.get_mut(&id) {
                row.lock_indicator = state;
            }
        }
        Msg::FsDetailDropdown(dad::IdMsg(id, msg)) => {
            dad::update(
                dad::IdMsg(id, msg),
                &mut model.fs_detail.dropdown,
                &mut orders.proxy(Msg::FsDetailDropdown),
            );
        }
        Msg::CloseMountModal => {
            model.mount_modal_open = false;
        }
        Msg::OpenMountModal => {
            model.mount_modal_open = true;
        }
        Msg::InodeTable(msg) => {
            iml_stratagem::update(
                msg,
                &mut model.stratagem,
                &mut orders.proxy(Msg::InodeTable),
            );
        }
        Msg::StratagemInit(msg) => {
            model.stratagem_ready = model.stratagem_ready();

            orders.send_msg(Msg::StratagemComponent(msg));
        }
        Msg::StratagemComponent(msg) => {
            iml_stratagem::update(
                msg,
                &mut model.stratagem,
                &mut orders.proxy(Msg::StratagemComponent),
            );
        }
        Msg::ScanNow(msg) => {
            iml_stratagem::scan_now::update(
                msg,
                &mut model.scan_now,
                &mut orders.proxy(Msg::ScanNow),
            );
        }
    }
}

fn detail_header<T>(header: &str) -> Node<T> {
    h4![
        header,
        style! {
            "color" => "#777",
            "grid-column" => "1 / span 2",
            "grid-row-end" => "1",
        }
    ]
}

fn detail_panel<T>(children: Vec<Node<T>>) -> Node<T> {
    well(children)
        .add_style("display", "grid")
        .add_style("grid-template-columns", "50% 50%")
        .add_style("grid-row-gap", px(20))
}

fn detail_label<T>(content: &str) -> Node<T> {
    div![
        content,
        style! { "font-weight" => "700", "color" => "#777" }
    ]
}

fn filesystem(
    fs: &Filesystem,
    alerts: &[Alert],
    fs_detail: &FsDetail,
    mgt_el: Node<Msg>,
) -> Node<Msg> {
    detail_panel(vec![
        detail_header(&format!("{} Details", fs.name)),
        detail_label("Space Usage"),
        div![space_usage(
            fs.bytes_total.and_then(|x| fs.bytes_free.map(|y| x - y)),
            fs.bytes_total
        )],
        detail_label("File Usage"),
        div![file_usage(
            fs.files_total.and_then(|x| fs.files_free.map(|y| x - y)),
            fs.files_total
        )],
        detail_label("State"),
        div![fs.state],
        detail_label("Management Server"),
        div![mgt_el],
        detail_label("MDTs"),
        div![fs.mdts.len().to_string()],
        detail_label("OSTs"),
        div![fs.osts.len().to_string()],
        detail_label("Mounted Clients"),
        div![client_count(fs.client_count)],
        detail_label("Alerts"),
        div![alert_indicator(
            &alerts,
            0,
            &fs.resource_uri,
            fs_detail.alert_indicator.is_open()
        )
        .map_message(Msg::FsDetailPopoverState)],
        div![
            class!["full-width"],
            style! { "grid-column" => "1 / span 2" },
            dad::render(fs.id, &fs_detail.dropdown, fs)
                .map_message(Msg::FsDetailDropdown)
                .add_style("grid-column", "1 / span 2")
        ],
    ])
}

fn client_mount_details(fs_name: &str, details: impl Into<Cow<'static, str>>) -> Vec<Node<Msg>> {
    let close_btn = bs_button::btn(
        class![bs_button::BTN_DEFAULT],
        vec![
            Node::new_text("Close"),
            i![class!["far", "fa-times-circle"]],
        ],
    )
    .add_listener(simple_ev(Ev::Click, Msg::CloseMountModal));

    vec![
        bs_modal::backdrop(),
        bs_modal::modal(vec![
            bs_modal::header(vec![h4![format!("{} client mount command", fs_name)]]),
            bs_modal::body(vec![
                div![
                    style! { "padding-bottom" => px(10) },
                    "To mount this filesystem on a Lustre client, use the following command:"
                ],
                well(vec![Node::new_text(details)]),
            ]),
            bs_modal::footer(vec![close_btn]),
        ]),
    ]
}

fn ui_link<T>(path: &str, label: &str) -> Node<T> {
    link(&format!("{}{}", ui_root(), path), label)
}

fn target_table(
    xs: &[Target<TargetConfParam>],
    alerts: &[Alert],
    locks: &Locks,
    table_rows: &HashMap<u32, TableRow>,
) -> Node<Msg> {
    bs_table::table(
        Attrs::empty(),
        vec![
            thead![tr![
                th!["Name"],
                th!["Volume"],
                th![class!["hidden-xs"], "Primary Server"],
                th![class!["hidden-xs"], "Failover Server"],
                th!["Started on"],
                th!["Status"],
                th!["Actions"],
            ]],
            tbody![xs.iter().map(|x| tr![
                td![
                    class!["col-sm-1", "col-xs-2"],
                    style! {"word-break" => "break-all"},
                    ui_link(&format!("target/{}", x.id), &x.name)
                ],
                td![
                    class!["col-sm-3", "col-xs-2"],
                    style! {"word-break" => "break-all"},
                    x.volume_name
                ],
                td![
                    class!["hidden-xs"],
                    server_link(&x.primary_server, &x.primary_server_name)
                ],
                td![
                    class!["hidden-xs"],
                    server_link(
                        &x.failover_servers.first().unwrap_or(&"".into()),
                        &x.failover_server_name
                    )
                ],
                td![server_link(
                    x.active_host.as_ref().unwrap_or(&"".into()),
                    &x.active_host_name
                )],
                match table_rows.get(&x.id) {
                    Some(row) => vec![
                        td![
                            class!["col-sm-3"],
                            lock_indicator(
                                x.id,
                                row.lock_indicator.is_open(),
                                x.composite_id(),
                                &locks
                            )
                            .add_style("margin-right", px(5))
                            .map_message(Msg::FsRowLockIndicatorState),
                            alert_indicator(
                                &alerts,
                                x.id,
                                &x.resource_uri,
                                row.alert_indicator.is_open()
                            )
                            .map_message(Msg::FsRowIndicatorState)
                        ],
                        td![dad::render(x.id, &row.dropdown, x).map_message(Msg::FsRowDropdown)]
                    ],
                    None => vec![td![], td![]],
                }
            ])],
        ],
    )
}

fn view(model: &Model) -> Node<Msg> {
    let mnt_info_btn = bs_button::btn(
        class![bs_button::BTN_DEFAULT],
        vec![
            Node::new_text("View Client Mount Information"),
            i![class!["fas", "fa-info-circle"]],
        ],
    )
    .add_listener(simple_ev(Ev::Click, Msg::OpenMountModal));

    match &model.fs {
        Some(fs) => div![
            filesystem(
                &fs,
                &model.alerts,
                &model.fs_detail,
                mgt_link(model.mgt.first()),
            ),
            mnt_info_btn,
            if model.stratagem_ready {
                iml_stratagem::scan_now::view(fs.id, &model.scan_now).map_message(Msg::ScanNow)
            } else {
                vec![]
            },
            if model.mount_modal_open {
                client_mount_details(&fs.name, fs.mount_command.clone())
            } else {
                vec![]
            },
            if model.stratagem_ready {
                iml_stratagem::view(&model.stratagem).map_message(Msg::StratagemComponent)
            } else {
                seed::empty()
            },
            h4![class!["section-header"], format!("{} Targets", fs.name)],
            if model.mgt.is_empty() {
                vec![]
            } else {
                vec![
                    h5![class!["section-header"], "Management Target"],
                    target_table(&model.mgt, &model.alerts, &model.locks, &model.table_rows),
                ]
            },
            if model.mdts.is_empty() {
                vec![]
            } else {
                vec![
                    h5![class!["section-header"], "Metadata Targets"],
                    target_table(
                        &model.mdts[model.mdt_paging.offset()..model.mdt_paging.end()],
                        &model.alerts,
                        &model.locks,
                        &model.table_rows,
                    ),
                    paging(&model.mdt_paging).map_message(Msg::MdtPaging),
                ]
            },
            if model.osts.is_empty() {
                vec![]
            } else {
                vec![
                    h5![class!["section-header"], "Object Storage Targets"],
                    target_table(
                        &model.osts[model.ost_paging.offset()..model.ost_paging.end()],
                        &model.alerts,
                        &model.locks,
                        &model.table_rows,
                    ),
                    paging(&model.ost_paging)
                        .add_style("margin-bottom", px(50))
                        .map_message(Msg::OstPaging),
                ]
            }
        ],
        None => div!["Filesystem does not exist"],
    }
}

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed {
        return vec![];
    }

    vec![simple_ev(Ev::Click, Msg::WindowClick)]
}

#[wasm_bindgen]
pub struct FsDetailPageCallbacks {
    app: seed::App<Msg, Model, Node<Msg>>,
}

#[wasm_bindgen]
impl FsDetailPageCallbacks {
    pub fn destroy(&self) {
        self.app.update(Msg::Destroy);
    }
    pub fn set_filesystem(&self, filesystem: JsValue) {
        self.app
            .update(Msg::Filesystem(filesystem.into_serde_opt().unwrap()));
    }
    pub fn set_targets(&self, targets: JsValue) {
        self.app.update(Msg::Targets(targets.into_serde().unwrap()))
    }
    pub fn set_hosts(&self, hosts: JsValue) {
        self.app.update(Msg::Hosts(hosts.into_serde().unwrap()));
    }
    pub fn set_alerts(&self, alerts: JsValue) {
        self.app.update(Msg::Alerts(alerts.into_serde().unwrap()))
    }
    pub fn set_locks(&self, locks: JsValue) {
        self.app.update(Msg::Locks(locks.into_serde().unwrap()));
    }
    pub fn set_stratagem_configuration(&self, config: JsValue) {
        self.app
            .update(Msg::StratagemInit(iml_stratagem::Msg::SetConfig(
                config.into_serde_opt().unwrap(),
            )));
    }
    pub fn fetch_inode_table(&self) {
        self.app
            .update(Msg::InodeTable(iml_stratagem::Msg::InodeTable(
                iml_stratagem::inode_table::Msg::FetchInodes,
            )));
    }
    pub fn command_modal_closed(&self) {
        self.app.update(Msg::CloseCommandModal);
    }
}

fn init(_: Url, _orders: &mut impl Orders<Msg>) -> Model {
    Model::default()
}

#[wasm_bindgen]
pub fn render_fs_detail_page(el: Element) -> FsDetailPageCallbacks {
    init_log();

    let app = seed::App::build(init, update, view)
        .mount(el)
        .window_events(window_events)
        .finish()
        .run();

    FsDetailPageCallbacks { app: app.clone() }
}
