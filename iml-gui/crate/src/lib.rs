// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![allow(clippy::used_underscore_binding)]
#![allow(clippy::non_ascii_literal)]
#![allow(clippy::enum_glob_use)]

pub mod components;
pub mod dependency_tree;
pub mod key_codes;
pub mod page;
pub mod resize_observer;

mod auth;
mod breakpoints;
mod ctx_help;
mod environment;
mod event_source;
mod extensions;
mod generated;
mod notification;
mod route;
mod sleep;
mod status_section;
mod watch_state;

#[cfg(test)]
mod test_utils;

use components::{
    breadcrumbs, command_modal, date, font_awesome, font_awesome_outline, loading, restrict, stratagem, tree,
    update_activity_health, ActivityHealth,
};
pub(crate) use extensions::*;
use futures::channel::oneshot;
use generated::css_classes::C;
use iml_wire_types::{
    db::{ManagedTargetRecord, TargetRecord},
    warp_drive::ArcCache,
    warp_drive::{self, ArcRecord},
    Conf, GroupType,
};
use lazy_static::lazy_static;
use page::{Page, RecordChange};
use route::Route;
use seed::{app::MessageMapper, prelude::*, EventHandler, *};
pub(crate) use sleep::sleep_with_handle;
use std::{cmp, ops::Deref as _, sync::Arc};
pub use watch_state::*;
use web_sys::MessageEvent;
use Visibility::*;

const TITLE_SUFFIX: &str = "IML";
const STATIC_PATH: &str = "static";
const SLIDER_WIDTH_PX: u32 = 5;
const MAX_SIDE_PERCENTAGE: f32 = 35_f32;

/// This depends on where and how https://github.com/whamcloud/Online-Help is deployed.
/// With `nginx` when config is like
/// ```
/// location /help {
///     alias /usr/lib/iml-manager/iml-online-help;
///     index index.html;
/// }
/// ```
/// help url becomes `https://localhost:8443/help/docs/Graphical_User_Interface_9_0.html`
const HELP_PATH: &str = "help";

lazy_static! {
    static ref IS_PRODUCTION: bool = window()
        .get("IS_PRODUCTION")
        .expect("IS_PRODUCTION global variable not set.")
        .as_bool()
        .expect("IS_PRODUCTION global variable is not a boolean.");
}

lazy_static! {
    static ref UI_BASE: Option<String> = ui_base();
}

fn ui_base() -> Option<String> {
    let x = document().base_uri().unwrap().unwrap_or_default();

    let url = web_sys::Url::new(&x).unwrap();

    let base = url.href().replace(&url.origin(), "").replace('/', "");

    match base.as_str() {
        "" => None,
        _ => Some(base),
    }
}

#[derive(Clone, Copy, Eq, PartialEq, Debug)]
pub enum Visibility {
    Visible,
    Hidden,
}

impl Visibility {
    pub fn toggle(&mut self) {
        *self = match self {
            Visible => Hidden,
            Hidden => Visible,
        }
    }
}

struct Loading {
    session: Option<oneshot::Sender<()>>,
    messages: Option<oneshot::Sender<()>>,
    locks: Option<oneshot::Sender<()>>,
    conf: Option<oneshot::Sender<()>>,
}

impl Loading {
    /// Do we have enough data to load the app?
    fn loaded(&self) -> bool {
        self.session
            .as_ref()
            .or_else(|| self.messages.as_ref())
            .or_else(|| self.locks.as_ref())
            .or_else(|| self.conf.as_ref())
            .is_none()
    }
}

struct BreadCrumb {
    href: String,
    title: String,
}

impl breadcrumbs::BreadCrumb for BreadCrumb {
    fn href(&self) -> &str {
        &self.href
    }
    fn title(&self) -> &str {
        &self.title
    }
}

impl PartialEq for BreadCrumb {
    fn eq(&self, other: &Self) -> bool {
        self.href == other.href
    }
}

// ------ ------
//     Model
// ------ ------

pub struct Model {
    activity_health: ActivityHealth,
    auth: auth::Model,
    breadcrumbs: breadcrumbs::BreadCrumbs<BreadCrumb>,
    breakpoint_size: breakpoints::Size,
    command_modal: command_modal::Model,
    conf: Conf,
    loading: Loading,
    locks: warp_drive::Locks,
    manage_menu_state: WatchState,
    menu_visibility: Visibility,
    notification: notification::Model,
    page: Page,
    records: warp_drive::ArcCache,
    route: Route<'static>,
    side_width_percentage: f32,
    status_section: status_section::Model,
    track_slider: bool,
    tree: tree::Model,
    server_date: date::Model,
}

// ------ ------
// Before Mount
// ------ ------

fn before_mount(_: Url) -> BeforeMount {
    BeforeMount::new().mount_point("app").mount_type(MountType::Takeover)
}

// ------ ------
//  After Mount
// ------ ------

fn after_mount(url: Url, orders: &mut impl Orders<Msg, GMsg>) -> AfterMount<Model> {
    event_source::init(orders);

    orders.send_msg(Msg::UpdatePageTitle);

    orders.send_msg(Msg::FetchConf);

    orders.proxy(Msg::Notification).perform_cmd(notification::init());

    orders.proxy(Msg::Auth).send_msg(Box::new(auth::Msg::Fetch));

    let (session_tx, session_rx) = oneshot::channel();
    let (messages_tx, messages_rx) = oneshot::channel();
    let (locks_tx, locks_rx) = oneshot::channel();
    let (conf_tx, conf_rx) = oneshot::channel();

    let fut = async {
        let (r1, r2, r3, r4) = futures::join!(session_rx, messages_rx, locks_rx, conf_rx);

        if let Err(e) = r1.or(r2).or(r3).or(r4) {
            error!(format!("Could not load initial data: {:?}", e));
        }

        Ok(Msg::LoadPage)
    };

    orders.perform_cmd(fut);

    AfterMount::new(Model {
        activity_health: ActivityHealth::default(),
        auth: auth::Model::default(),
        breadcrumbs: breadcrumbs::BreadCrumbs::default(),
        breakpoint_size: breakpoints::size(),
        command_modal: command_modal::Model::default(),
        conf: Conf::default(),
        loading: Loading {
            session: Some(session_tx),
            messages: Some(messages_tx),
            locks: Some(locks_tx),
            conf: Some(conf_tx),
        },
        locks: im::hashmap!(),
        manage_menu_state: WatchState::default(),
        menu_visibility: Visible,
        notification: notification::Model::default(),
        page: Page::AppLoading,
        records: warp_drive::ArcCache::default(),
        route: url.into(),
        side_width_percentage: 20_f32,
        status_section: status_section::Model::default(),
        track_slider: false,
        tree: tree::Model::default(),
        server_date: date::Model::default(),
    })
}

// ------ ------
//    Routes
// ------ ------

pub fn routes(url: Url) -> Option<Msg> {
    let pth = url.get_path();

    // Some URLs are files => treat them as external links.
    if pth.starts_with(&[STATIC_PATH.into()])
        || pth.starts_with(&[HELP_PATH.into()])
        || pth.starts_with(&["api".into(), "report".into()])
    {
        return None;
    }
    Some(Msg::RouteChanged(url))
}

// ------ ------
//     Sink
// ------ ------

#[allow(clippy::large_enum_variant)]
pub enum GMsg {
    RouteChange(Url),
    AuthProxy(Box<auth::Msg>),
    ServerDate(chrono::DateTime<chrono::offset::FixedOffset>),
    OpenCommandModal(command_modal::Input),
    UpdatePageTitle,
}

fn sink(g_msg: GMsg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match g_msg {
        GMsg::UpdatePageTitle => {
            orders.send_msg(Msg::UpdatePageTitle);
        }
        GMsg::RouteChange(url) => {
            seed::push_route(url.clone());
            orders.send_msg(Msg::RouteChanged(url));
        }
        GMsg::AuthProxy(msg) => {
            orders.proxy(Msg::Auth).send_msg(msg);
        }
        GMsg::ServerDate(d) => model.server_date.basedate = Some(d),
        GMsg::OpenCommandModal(x) => {
            orders
                .proxy(Msg::CommandModal)
                .send_msg(command_modal::Msg::FireCommands(x));
        }
    }
}

// ------ ------
//    Update
// ------ ------

#[allow(clippy::large_enum_variant)]
#[derive(Clone, Debug)]
pub enum Msg {
    Auth(Box<auth::Msg>),
    CommandModal(command_modal::Msg),
    EventSourceConnect(JsValue),
    EventSourceError(JsValue),
    EventSourceMessage(MessageEvent),
    FetchConf,
    FetchedConf(fetch::ResponseDataResult<Conf>),
    HideMenu,
    LoadPage,
    Locks(warp_drive::Locks),
    ManageMenuState,
    Notification(notification::Msg),
    RecordChange(Box<warp_drive::RecordChange>),
    Records(Box<warp_drive::Cache>),
    RemoveRecord(warp_drive::RecordId),
    RouteChanged(Url),
    StatusSection(status_section::Msg),
    SliderX(i32, f64),
    StartSliderTracking,
    StopSliderTracking,
    ToggleMenu,
    Tree(tree::Msg),
    Page(page::Msg),
    UpdatePageTitle,
    WindowClick,
    WindowResize,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::RouteChanged(url) => {
            model.route = Route::from(url);

            if model.route == Route::Dashboard {
                model.breadcrumbs.clear();
            }

            orders.send_msg(Msg::LoadPage);
        }
        Msg::UpdatePageTitle => {
            let title = model.page.title();
            document().set_title(&format!("{} - {}", &title, TITLE_SUFFIX));
            model.breadcrumbs.push(BreadCrumb {
                href: model.route.to_href(),
                title,
            });
        }
        Msg::EventSourceConnect(_) => {
            log("EventSource connected.");
        }
        Msg::FetchConf => {
            let fut = fetch::Request::api_call("conf").fetch_json_data(Msg::FetchedConf);

            orders.perform_cmd(fut);
        }
        Msg::FetchedConf(r) => {
            match r {
                Ok(c) => {
                    model.conf = c;

                    if let Some(tx) = model.loading.conf.take() {
                        let _ = tx.send(());
                    }
                }
                Err(e) => {
                    error!("Unable to fetch conf", e);
                }
            };
        }
        Msg::LoadPage => {
            if model.loading.loaded() && !model.page.is_active(&model.route) {
                if (model.route == Route::Snapshots && !model.conf.use_snapshots)
                    || (model.route == Route::Stratagem && !model.conf.use_stratagem)
                {
                    model.route = Route::NotFound;
                }

                model.page = (&model.records, &model.conf, &model.route).into();
                orders.send_msg(Msg::UpdatePageTitle);
                model.page.init(&model.records, &mut orders.proxy(Msg::Page));
            } else {
                orders.skip();
            }
        }
        Msg::EventSourceMessage(msg) => {
            let txt = msg.data().as_string().unwrap();

            let msg: warp_drive::Message = serde_json::from_str(&txt).unwrap();

            let msg = match msg {
                warp_drive::Message::Locks(locks) => {
                    if let Some(locks) = model.loading.locks.take() {
                        let _ = locks.send(());
                    }

                    Msg::Locks(locks)
                }
                warp_drive::Message::Records(records) => {
                    if let Some(messages) = model.loading.messages.take() {
                        let _ = messages.send(());
                    }

                    Msg::Records(Box::new(records))
                }
                warp_drive::Message::RecordChange(record_change) => Msg::RecordChange(Box::new(record_change)),
            };

            orders.skip().send_msg(msg);
        }
        Msg::EventSourceError(_) => {
            log("EventSource error.");
        }
        Msg::Records(records) => {
            model.records = (&*records).into();

            model.page.set_records(&model.records, &mut orders.proxy(Msg::Page));

            let old = model.activity_health;
            model.activity_health = update_activity_health(&model.records.active_alert);

            orders
                .proxy(Msg::Notification)
                .send_msg(notification::generate(None, &old, &model.activity_health));

            orders
                .proxy(Msg::Page)
                .proxy(page::Msg::Servers)
                .send_msg(page::servers::Msg::SetHosts(
                    model.records.host.values().cloned().collect(),
                    model.records.lnet_configuration.clone(),
                    model.records.pacemaker_configuration.clone(),
                    model.records.corosync_configuration.clone(),
                ));

            orders
                .proxy(Msg::Page)
                .proxy(page::Msg::Filesystems)
                .send_msg(page::filesystems::Msg::SetFilesystems(
                    model.records.filesystem.values().cloned().collect(),
                ));

            orders
                .proxy(Msg::Page)
                .proxy(page::Msg::Filesystem)
                .send_msg(page::filesystem::Msg::SetTargets(
                    model.records.target.values().cloned().collect(),
                ));

            orders
                .proxy(Msg::Page)
                .proxy(page::Msg::Filesystem)
                .proxy(page::filesystem::Msg::Stratagem)
                .send_msg(stratagem::Msg::SetStratagemConfig(
                    model.records.stratagem_config.values().cloned().collect(),
                ));

            orders
                .proxy(Msg::Page)
                .proxy(page::Msg::Mgts)
                .send_msg(page::mgts::Msg::SetTargets(
                    model.records.target.values().cloned().collect(),
                ));

            orders.proxy(Msg::Tree).send_msg(tree::Msg::Reset);
        }
        Msg::RecordChange(record_change) => {
            handle_record_change(*record_change, model, orders);
        }
        Msg::RemoveRecord(id) => {
            model.records.remove_record(id);

            model
                .page
                .remove_record(id, &model.records, &mut orders.proxy(Msg::Page));

            match id {
                warp_drive::RecordId::Host(_) => {
                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Servers)
                        .send_msg(page::servers::Msg::SetHosts(
                            model.records.host.values().cloned().collect(),
                            model.records.lnet_configuration.clone(),
                            model.records.pacemaker_configuration.clone(),
                            model.records.corosync_configuration.clone(),
                        ));
                }
                warp_drive::RecordId::Filesystem(x) => {
                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Filesystems)
                        .send_msg(page::filesystems::Msg::RemoveFilesystem(x));
                }
                warp_drive::RecordId::Target(x) => {
                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Filesystem)
                        .send_msg(page::filesystem::Msg::RemoveTarget(x));

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Mgts)
                        .send_msg(page::mgts::Msg::RemoveTarget(x));
                }
                warp_drive::RecordId::ActiveAlert(_) => {
                    let old = model.activity_health;
                    model.activity_health = update_activity_health(&model.records.active_alert);

                    orders.proxy(Msg::Notification).send_msg(notification::generate(
                        None,
                        &old,
                        &model.activity_health,
                    ));
                }
                _ => {}
            }
        }
        Msg::Locks(locks) => {
            model.locks = locks;
        }
        Msg::ToggleMenu => model.menu_visibility.toggle(),
        Msg::ManageMenuState => {
            model.manage_menu_state.update();
        }
        Msg::HideMenu => {
            model.menu_visibility = Hidden;
        }

        Msg::StartSliderTracking => {
            model.track_slider = true;
        }
        Msg::StopSliderTracking => {
            model.track_slider = false;
        }
        Msg::SliderX(x_position, page_width) => {
            let overlay_width_px = page_width as u32 - SLIDER_WIDTH_PX;

            let x_position = cmp::max(0, x_position) as u32;

            let side_width_percentage: f32 = (x_position as f32 / overlay_width_px as f32) * 100_f32;

            model.side_width_percentage = if MAX_SIDE_PERCENTAGE <= side_width_percentage {
                MAX_SIDE_PERCENTAGE
            } else {
                side_width_percentage
            };
        }
        Msg::StatusSection(msg) => {
            status_section::update(
                msg,
                &model.records,
                &mut model.status_section,
                &mut orders.proxy(Msg::StatusSection),
            );
        }
        Msg::WindowClick => {
            if model.manage_menu_state.should_update() {
                model.manage_menu_state.update();
            }
        }
        Msg::WindowResize => {
            model.breakpoint_size = breakpoints::size();

            if model.menu_visibility == Visibility::Visible {
                orders.skip();
            }
        }
        Msg::Notification(nu) => {
            notification::update(nu, &mut model.notification, &mut orders.proxy(Msg::Notification));
        }
        Msg::Tree(msg) => {
            tree::update(&model.records, msg, &mut model.tree, &mut orders.proxy(Msg::Tree));
        }

        Msg::Auth(msg) => {
            if let (Some(_), Some(session)) = (model.auth.get_session(), model.loading.session.take()) {
                let _ = session.send(());
            }

            auth::update(*msg, &mut model.auth, &mut orders.proxy(|x| Msg::Auth(Box::new(x))));
        }
        Msg::Page(msg) => {
            page::update(msg, &mut model.page, &model.records, &mut orders.proxy(Msg::Page));
        }
        Msg::CommandModal(msg) => {
            command_modal::update(msg, &mut model.command_modal, &mut orders.proxy(Msg::CommandModal));
        }
    }
}

fn handle_record_change(
    record_change: warp_drive::RecordChange,
    model: &mut Model,
    orders: &mut impl Orders<Msg, GMsg>,
) {
    match record_change {
        warp_drive::RecordChange::Update(record) => {
            let record = ArcRecord::from(record);

            match record.clone() {
                ArcRecord::ActiveAlert(x) => {
                    let msg = x.message.clone();

                    model.records.active_alert.insert(x.id, x);

                    let old = model.activity_health;

                    model.activity_health = update_activity_health(&model.records.active_alert);
                    orders.proxy(Msg::Notification).send_msg(notification::generate(
                        Some(msg),
                        &old,
                        &model.activity_health,
                    ));
                }
                ArcRecord::Filesystem(x) => {
                    let id = x.id;

                    if model.records.filesystem.insert(id, Arc::clone(&x)).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::Filesystem(id)));
                    }

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Filesystems)
                        .send_msg(page::filesystems::Msg::AddFilesystem(x));
                }
                ArcRecord::ContentType(x) => {
                    model.records.content_type.insert(x.id, x);
                }
                ArcRecord::Group(x) => {
                    model.records.group.insert(x.id, x);
                }
                ArcRecord::Host(x) => {
                    let id = x.id;
                    if model.records.host.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::Host(id)));
                    };

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Servers)
                        .send_msg(page::servers::Msg::SetHosts(
                            model.records.host.values().cloned().collect(),
                            model.records.lnet_configuration.clone(),
                            model.records.pacemaker_configuration.clone(),
                            model.records.corosync_configuration.clone(),
                        ));
                }
                ArcRecord::ManagedTargetMount(x) => {
                    model.records.managed_target_mount.insert(x.id, x);
                }
                ArcRecord::OstPool(x) => {
                    model.records.ost_pool.insert(x.id, x);
                }
                ArcRecord::OstPoolOsts(x) => {
                    let id = x.id;
                    if model.records.ost_pool_osts.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::OstPoolOsts(id)));
                    };
                }
                ArcRecord::SfaDiskDrive(x) => {
                    model.records.sfa_disk_drive.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::SfaEnclosure(x) => {
                    model.records.sfa_enclosure.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::SfaStorageSystem(x) => {
                    model.records.sfa_storage_system.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::SfaJob(x) => {
                    model.records.sfa_job.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::SfaPowerSupply(x) => {
                    model.records.sfa_power_supply.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::SfaController(x) => {
                    model.records.sfa_controller.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::Snapshot(x) => {
                    model.records.snapshot.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::SnapshotInterval(x) => {
                    model.records.snapshot_interval.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::SnapshotRetention(x) => {
                    model.records.snapshot_retention.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::StratagemConfig(x) => {
                    model.records.stratagem_config.insert(x.id, Arc::clone(&x));

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Filesystem)
                        .proxy(page::filesystem::Msg::Stratagem)
                        .send_msg(stratagem::Msg::UpdateStratagemConfig(x));
                }
                ArcRecord::Target(x) => {
                    let id = x.id;

                    if model.records.target.insert(x.id, Arc::clone(&x)).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::Target(id)));
                    };

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Filesystem)
                        .send_msg(page::filesystem::Msg::AddTarget(Arc::clone(&x)));

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Target)
                        .send_msg(page::target::Msg::UpdateTarget(Arc::clone(&x)));

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Mgts)
                        .send_msg(page::mgts::Msg::AddTarget(x));
                }
                ArcRecord::TargetRecord(x) => {
                    model.records.target_record.insert(x.id, Arc::clone(&x));
                }
                ArcRecord::User(x) => {
                    model.records.user.insert(x.id, Arc::clone(&x));

                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::User)
                        .send_msg(page::user::Msg::SetUser(x));
                }
                ArcRecord::UserGroup(x) => {
                    model.records.user_group.insert(x.id, x);
                }
                ArcRecord::Volume(x) => {
                    model.records.volume.insert(x.id, x);
                }
                ArcRecord::VolumeNode(x) => {
                    let id = x.id;
                    if model.records.volume_node.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::VolumeNode(id)));
                    };
                }
                ArcRecord::LnetConfiguration(x) => {
                    model.records.lnet_configuration.insert(x.id, x);
                }
                ArcRecord::CorosyncConfiguration(x) => {
                    model.records.corosync_configuration.insert(x.id, x);
                }
                ArcRecord::PacemakerConfiguration(x) => {
                    model.records.pacemaker_configuration.insert(x.id, x);
                }
            }

            model
                .page
                .update_record(record, &model.records, &mut orders.proxy(Msg::Page));
        }
        warp_drive::RecordChange::Delete(record_id) => {
            match record_id {
                warp_drive::RecordId::Filesystem(_)
                | warp_drive::RecordId::VolumeNode(_)
                | warp_drive::RecordId::Host(_)
                | warp_drive::RecordId::OstPoolOsts(_)
                | warp_drive::RecordId::Target(_) => {
                    orders.proxy(Msg::Tree).send_msg(tree::Msg::Remove(record_id));
                }
                warp_drive::RecordId::StratagemConfig(_) => {
                    orders
                        .proxy(Msg::Page)
                        .proxy(page::Msg::Filesystem)
                        .proxy(page::filesystem::Msg::Stratagem)
                        .send_msg(stratagem::Msg::DeleteStratagemConfig);
                }
                _ => {}
            };

            orders.send_msg(Msg::RemoveRecord(record_id));
        }
    }
}

// ------ ------
//     View
// ------ ------

pub fn main_panels(model: &Model, children: impl View<page::Msg>) -> impl View<Msg> {
    div![
        class![
            C.fade_in,
            C.min_h_screen,
            C.flex,
            C.flex_col,
            C.select_none => model.track_slider
        ],
        // slider overlay
        if model.track_slider {
            div![
                class![C.w_full, C.h_full, C.fixed, C.top_0, C.cursor_ew_resize,],
                style! { St::ZIndex => 9999 },
                mouse_ev(Ev::MouseMove, |ev| {
                    let target = ev.target().unwrap();
                    let el = seed::to_html_el(&target);

                    let rect = el.get_bounding_client_rect();

                    Msg::SliderX(ev.client_x(), rect.width())
                }),
            ]
        } else {
            empty![]
        },
        page::partial::header::view(model).els(),
        // panel container
        div![
            class![C.flex, C.flex_wrap, C.flex_col, C.lg__flex_row, C.flex_grow],
            // side panel
            restrict::view(
                model.auth.get_session(),
                GroupType::FilesystemAdministrators,
                div![
                    class![
                        C.flex_grow_0,
                        C.flex_shrink_0,
                        C.overflow_x_hidden,
                        C.overflow_y_auto,
                        C.whitespace_no_wrap,
                        C.bg_blue_1000,
                        C.border_r_2,
                        C.border_gray_800,
                        C.lg__h_main_content,
                    ],
                    style! { St::FlexBasis => percent(model.side_width_percentage) },
                    tree::view(&model.records, &model.tree).map_msg(Msg::Tree)
                ]
            ),
            // slider panel
            restrict::view(
                model.auth.get_session(),
                GroupType::FilesystemAdministrators,
                div![
                    class![
                        C.bg_gray_600,
                        C.bg_green_400 => model.track_slider,
                        C.cursor_ew_resize,
                        C.flex_grow_0,
                        C.flex_shrink_0,
                        C.hidden
                        C.hover__bg_green_400,
                        C.lg__block,
                        C.lg__h_main_content,
                        C.relative,
                    ],
                    simple_ev(Ev::MouseDown, Msg::StartSliderTracking),
                    style! {
                        St::FlexBasis => px(SLIDER_WIDTH_PX),
                    },
                    div![
                        class![C.absolute, C.rounded],
                        style! {
                            St::BackgroundColor => "inherit",
                            St::Height => px(64),
                            St::Width => px(18),
                            St::Top => "calc(50% - 32px)",
                            St::Left => px(-7.5),
                        }
                    ]
                ]
            ),
            // main panel
            div![
                class![
                    C.flex,
                    C.flex_col,
                    C.flex_grow,
                    C.flex_shrink_0,
                    C.bg_gray_300,
                    C.lg__w_0,
                    C.lg__h_main_content,
                ],
                // main content
                div![
                    class![C.flex_grow, C.overflow_x_auto, C.overflow_y_auto, C.p_6],
                    children.els().map_msg(Msg::Page)
                ],
                page::partial::footer::view(&model.conf).els(),
            ],
            // Side buttons panel
            status_section::view(
                &model.status_section,
                &model.route,
                &model.records,
                &model.activity_health,
                model.auth.get_session(),
                &model.locks,
                &model.server_date
            )
            .els()
            .map_msg(Msg::StatusSection)
        ],
    ]
}

fn view(model: &Model) -> Vec<Node<Msg>> {
    let nodes = match &model.page {
        Page::AppLoading => loading::view().els(),
        Page::About => main_panels(model, page::about::view(model).els().map_msg(page::Msg::About)).els(),
        Page::Dashboard(page) => main_panels(model, page::dashboard::view(page).map_msg(page::Msg::Dashboard)).els(),
        Page::Filesystems(page) => main_panels(
            model,
            page::filesystems::view(&model.records, page, &model.locks, model.auth.get_session())
                .els()
                .map_msg(page::Msg::Filesystems),
        )
        .els(),
        Page::Filesystem(page) => main_panels(
            model,
            page::filesystem::view(
                &model.records,
                page,
                &model.locks,
                model.auth.get_session(),
                model.conf.use_stratagem,
            )
            .els()
            .map_msg(page::Msg::Filesystem),
        )
        .els(),
        Page::ServerDashboard(page) => main_panels(
            model,
            page::server_dashboard::view(&model.records, page)
                .els()
                .map_msg(page::Msg::ServerDashboard),
        )
        .els(),
        Page::TargetDashboard(page) => main_panels(
            model,
            page::target_dashboard::view(&model.records, page)
                .els()
                .map_msg(page::Msg::TargetDashboard),
        )
        .els(),
        Page::FsDashboard(page) => {
            main_panels(model, page::fs_dashboard::view(page).map_msg(page::Msg::FsDashboard)).els()
        }
        Page::Jobstats => main_panels(model, page::jobstats::view(model).els().map_msg(page::Msg::Jobstats)).els(),
        Page::Login(x) => page::login::view(x, model.conf.branding, &model.conf.exa_version)
            .els()
            .map_msg(|x| page::Msg::Login(Box::new(x)))
            .map_msg(Msg::Page),
        Page::Mgts(x) => main_panels(
            model,
            page::mgts::view(&model.records, x, &model.locks, model.auth.get_session())
                .els()
                .map_msg(page::Msg::Mgts),
        )
        .els(),
        Page::NotFound => page::not_found::view(model).els(),
        Page::OstPools => main_panels(model, page::ostpools::view(model).els().map_msg(page::Msg::OstPools)).els(),
        Page::OstPool(x) => main_panels(model, page::ostpool::view(x).els().map_msg(page::Msg::OstPool)).els(),
        Page::PowerControl => main_panels(
            model,
            page::power_control::view(model).els().map_msg(page::Msg::PowerControl),
        )
        .els(),
        Page::Servers(page) => main_panels(
            model,
            page::servers::view(
                &model.records,
                model.auth.get_session(),
                page,
                &model.locks,
                &model.server_date,
            )
            .els()
            .map_msg(page::Msg::Servers),
        )
        .els(),
        Page::Server(x) => main_panels(
            model,
            page::server::view(
                &model.records,
                x,
                &model.locks,
                model.auth.get_session(),
                &model.server_date,
            )
            .els()
            .map_msg(page::Msg::Server),
        )
        .els(),
        Page::Targets => main_panels(model, page::targets::view(model).els().map_msg(page::Msg::Targets)).els(),
        Page::Target(x) => main_panels(
            model,
            page::target::view(&model.records, x, &model.locks, model.auth.get_session())
                .els()
                .map_msg(page::Msg::Target),
        )
        .els(),
        Page::Users => main_panels(model, page::users::view(&model.records).els().map_msg(page::Msg::Users)).els(),
        Page::User(x) => main_panels(model, page::user::view(x).els().map_msg(page::Msg::User)).els(),
        Page::Volumes(x) => main_panels(model, page::volumes::view(x).els().map_msg(page::Msg::Volumes)).els(),
        Page::ServerVolumes(x) => main_panels(model, page::volumes::view(x).els().map_msg(page::Msg::Volumes)).els(),
        Page::Volume(x) => main_panels(model, page::volume::view(x).els().map_msg(page::Msg::Volume)).els(),
        Page::SfaEnclosure(x) => main_panels(
            model,
            page::sfa_enclosure::view(&model.records, x)
                .els()
                .map_msg(page::Msg::SfaEnclosure),
        )
        .els(),
        Page::Snapshots(x) => main_panels(
            model,
            page::snapshot::view(x, &model.records, model.auth.get_session())
                .els()
                .map_msg(page::Msg::Snapshots),
        )
        .els(),
        Page::Stratagem(x) => main_panels(
            model,
            page::stratagem::view(x, model.auth.get_session())
                .els()
                .map_msg(page::Msg::Stratagem),
        )
        .els(),
    };

    // command modal is the global singleton, therefore is being showed here
    let modal = command_modal::view(&model.command_modal).map_msg(Msg::CommandModal);
    div![modal, nodes].els()
}

pub fn asset_path(asset: &str) -> String {
    format!("{}/{}", STATIC_PATH, asset)
}

// ------ ------
// Window Events
// ------ ------

pub fn window_events(model: &Model) -> Vec<EventHandler<Msg>> {
    let mut xs = vec![
        simple_ev(Ev::Click, Msg::WindowClick),
        simple_ev(Ev::Resize, Msg::WindowResize),
    ];

    if model.track_slider {
        xs.push(simple_ev(Ev::MouseUp, Msg::StopSliderTracking));
    }

    xs
}

// ------ ------
//     Start
// ------ ------

#[wasm_bindgen(start)]
pub fn run() {
    log!("Starting app...");

    App::builder(update, view)
        .before_mount(before_mount)
        .after_mount(after_mount)
        .routes(routes)
        .sink(sink)
        .window_events(window_events)
        .build_and_start();

    log!("App started.");
}

fn get_target_from_managed_target<'a>(cache: &'a ArcCache, x: &ManagedTargetRecord) -> Option<&'a TargetRecord> {
    cache
        .target_record
        .values()
        .find(|y| x.uuid.as_deref() == Some(y.uuid.as_str()))
        .map(|x| x.deref())
}
