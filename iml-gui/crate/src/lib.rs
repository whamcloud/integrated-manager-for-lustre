#![allow(clippy::used_underscore_binding)]
#![allow(clippy::non_ascii_literal)]
#![allow(clippy::enum_glob_use)]

pub mod components;
pub mod key_codes;
pub mod page;

mod auth;
mod breakpoints;
mod ctx_help;
mod environment;
mod event_source;
mod extensions;
mod generated;
mod notification;
mod route;
mod server_date;
mod sleep;
mod status_section;
mod watch_state;

#[cfg(test)]
mod test_utils;

use components::{
    breadcrumbs::BreadCrumbs, font_awesome, font_awesome_outline, loading, restrict, stratagem, tree,
    update_activity_health, ActivityHealth,
};
pub(crate) use extensions::*;
use futures::channel::oneshot;
use generated::css_classes::C;
use iml_wire_types::{
    warp_drive::{self, ArcValuesExt},
    GroupType, Session,
};
use lazy_static::lazy_static;
use page::{login, Page};
use regex::Regex;
use route::Route;
use seed::{app::MessageMapper, prelude::*, EventHandler, *};
pub(crate) use server_date::ServerDate;
pub(crate) use sleep::sleep_with_handle;
use std::{cmp, sync::Arc};
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

pub fn extract_id(s: &str) -> Option<&str> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"^/?api/[^/]+/(\d+)/?$").unwrap();
    }
    let x = RE.captures(s)?;

    x.get(1).map(|x| x.as_str())
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
}

impl Loading {
    /// Do we have enough data to load the app?
    fn loaded(&self) -> bool {
        self.session
            .as_ref()
            .or_else(|| self.messages.as_ref())
            .or_else(|| self.locks.as_ref())
            .is_none()
    }
}

// ------ ------
//     Model
// ------ ------

pub struct Model {
    activity_health: ActivityHealth,
    auth: auth::Model,
    breadcrumbs: BreadCrumbs<Route<'static>>,
    breakpoint_size: breakpoints::Size,
    loading: Loading,
    locks: warp_drive::Locks,
    logging_out: bool,
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
    server_date: ServerDate,
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

    orders.proxy(Msg::Notification).perform_cmd(notification::init());

    orders.proxy(Msg::Auth).send_msg(Box::new(auth::Msg::Fetch));

    let (session_tx, session_rx) = oneshot::channel();
    let (messages_tx, messages_rx) = oneshot::channel();
    let (locks_tx, locks_rx) = oneshot::channel();

    let fut = async {
        let (r1, r2, r3) = futures::join!(session_rx, messages_rx, locks_rx);

        if let Err(e) = r1.or(r2).or(r3) {
            error!(format!("Could not load initial data: {:?}", e));
        }

        Ok(Msg::LoadPage)
    };

    orders.perform_cmd(fut);

    AfterMount::new(Model {
        activity_health: ActivityHealth::default(),
        auth: auth::Model::default(),
        breadcrumbs: BreadCrumbs::default(),
        breakpoint_size: breakpoints::size(),
        loading: Loading {
            session: Some(session_tx),
            messages: Some(messages_tx),
            locks: Some(locks_tx),
        },
        locks: im::hashmap!(),
        logging_out: false,
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
        server_date: ServerDate::default(),
    })
}

// ------ ------
//    Routes
// ------ ------

pub fn routes(url: Url) -> Option<Msg> {
    let pth = url.get_path();

    // Urls which start with `static` are files => treat them as external links.
    if pth.starts_with(&[STATIC_PATH.into()]) || pth.starts_with(&[HELP_PATH.into()]) {
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
}

fn sink(g_msg: GMsg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match g_msg {
        GMsg::RouteChange(url) => {
            seed::push_route(url.clone());
            orders.send_msg(Msg::RouteChanged(url));
        }
        GMsg::AuthProxy(msg) => {
            orders.proxy(Msg::Auth).send_msg(msg);
        }
        GMsg::ServerDate(d) => model.server_date.set(d),
    }
}

// ------ ------
//    Update
// ------ ------

#[allow(clippy::large_enum_variant)]
#[derive(Clone)]
pub enum Msg {
    Auth(Box<auth::Msg>),
    EventSourceConnect(JsValue),
    EventSourceError(JsValue),
    EventSourceMessage(MessageEvent),
    FilesystemsPage(page::filesystems::Msg),
    FilesystemPage(page::filesystem::Msg),
    GetSession,
    GotSession(fetch::ResponseDataResult<Session>),
    HideMenu,
    LoadPage,
    Locks(warp_drive::Locks),
    LoggedOut(fetch::FetchObject<()>),
    Login(login::Msg),
    Logout,
    ManageMenuState,
    MgtsPage(page::mgts::Msg),
    Notification(notification::Msg),
    RecordChange(Box<warp_drive::RecordChange>),
    DashboardPage(page::dashboard::Msg),
    FsDashboardPage(page::fs_dashboard::Msg),
    Records(Box<warp_drive::Cache>),
    RemoveRecord(warp_drive::RecordId),
    RouteChanged(Url),
    ServersPage(page::servers::Msg),
    StatusSection(status_section::Msg),
    SliderX(i32, f64),
    StartSliderTracking,
    StopSliderTracking,
    TargetPage(page::target::Msg),
    ToggleMenu,
    Tree(tree::Msg),
    UpdatePageTitle,
    WindowClick,
    WindowResize,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::RouteChanged(url) => {
            model.route = Route::from(url);

            orders.send_msg(Msg::UpdatePageTitle);

            if model.route == Route::Login {
                orders.send_msg(Msg::Logout);
            }

            if model.route == Route::Dashboard {
                model.breadcrumbs.clear();
            }

            model.breadcrumbs.push(model.route.clone());

            orders.send_msg(Msg::LoadPage);
        }
        Msg::UpdatePageTitle => {
            let title = format!("{} - {}", model.route.to_string(), TITLE_SUFFIX);

            document().set_title(&title);
        }
        Msg::EventSourceConnect(_) => {
            log("EventSource connected.");
        }
        Msg::LoadPage => {
            if model.loading.loaded() && !model.page.is_active(&model.route) {
                model.page = (&model.records, &model.route).into();
                model.page.init(&model.records, orders);
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

            orders.send_msg(msg);
        }
        Msg::EventSourceError(_) => {
            log("EventSource error.");
        }
        Msg::GetSession => {
            orders
                .skip()
                .perform_cmd(auth::fetch_session().fetch_json_data(Msg::GotSession));
        }
        Msg::GotSession(data_result) => match data_result {
            Ok(resp) => {
                orders.send_g_msg(GMsg::AuthProxy(Box::new(auth::Msg::SetSession(resp))));

                model.logging_out = false;
            }
            Err(fail_reason) => {
                error!("Error fetching login session {:?}", fail_reason.message());

                orders.skip();
            }
        },
        Msg::Records(records) => {
            model.records = (&*records).into();

            let old = model.activity_health;
            model.activity_health = update_activity_health(&model.records.active_alert);

            orders
                .proxy(Msg::Notification)
                .send_msg(notification::generate(None, &old, &model.activity_health));

            orders.proxy(Msg::ServersPage).send_msg(page::servers::Msg::SetHosts(
                model.records.host.arc_values().cloned().collect(),
                model.records.lnet_configuration.clone(),
            ));

            orders
                .proxy(Msg::FilesystemsPage)
                .send_msg(page::filesystems::Msg::SetFilesystems(
                    model.records.filesystem.values().cloned().collect(),
                ));

            orders
                .proxy(Msg::FilesystemPage)
                .send_msg(page::filesystem::Msg::SetTargets(
                    model.records.target.values().cloned().collect(),
                ));

            orders
                .proxy(Msg::FilesystemPage)
                .proxy(page::filesystem::Msg::Stratagem)
                .send_msg(stratagem::Msg::CheckStratagem)
                .send_msg(stratagem::Msg::SetStratagemConfig(
                    model.records.stratagem_config.values().cloned().collect(),
                ));

            orders.proxy(Msg::MgtsPage).send_msg(page::mgts::Msg::SetTargets(
                model.records.target.values().cloned().collect(),
            ));

            orders.proxy(Msg::Tree).send_msg(tree::Msg::Reset);
        }
        Msg::RecordChange(record_change) => {
            handle_record_change(*record_change, model, orders);
        }
        Msg::RemoveRecord(id) => {
            model.records.remove_record(id);

            match id {
                warp_drive::RecordId::Host(_) => {
                    orders.proxy(Msg::ServersPage).send_msg(page::servers::Msg::SetHosts(
                        model.records.host.arc_values().cloned().collect(),
                        model.records.lnet_configuration.clone(),
                    ));

                    orders
                        .proxy(Msg::FilesystemPage)
                        .proxy(page::filesystem::Msg::Stratagem)
                        .send_msg(stratagem::Msg::CheckStratagem);
                }
                warp_drive::RecordId::Filesystem(x) => {
                    orders
                        .proxy(Msg::FilesystemsPage)
                        .send_msg(page::filesystems::Msg::RemoveFilesystem(x));
                }
                warp_drive::RecordId::Target(x) => {
                    orders
                        .proxy(Msg::FilesystemPage)
                        .send_msg(page::filesystem::Msg::RemoveTarget(x));

                    orders.proxy(Msg::MgtsPage).send_msg(page::mgts::Msg::RemoveTarget(x));

                    orders
                        .proxy(Msg::FilesystemPage)
                        .proxy(page::filesystem::Msg::Stratagem)
                        .send_msg(stratagem::Msg::CheckStratagem);
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
        Msg::ServersPage(msg) => {
            if let Page::Servers(page) = &mut model.page {
                page::servers::update(msg, &model.records, page, &mut orders.proxy(Msg::ServersPage))
            }
        }
        Msg::FilesystemPage(msg) => {
            if let Page::Filesystem(page) = &mut model.page {
                page::filesystem::update(msg, &model.records, page, &mut orders.proxy(Msg::FilesystemPage))
            }
        }
        Msg::FilesystemsPage(msg) => {
            if let Page::Filesystems(page) = &mut model.page {
                page::filesystems::update(msg, &model.records, page, &mut orders.proxy(Msg::FilesystemsPage))
            }
        }
        Msg::MgtsPage(msg) => {
            if let Page::Mgts(page) = &mut model.page {
                page::mgts::update(msg, &model.records, page, &mut orders.proxy(Msg::MgtsPage))
            }
        }
        Msg::TargetPage(msg) => {
            if let Page::Target(page) = &mut model.page {
                page::target::update(msg, &model.records, page, &mut orders.proxy(Msg::TargetPage))
            }
        }
        Msg::DashboardPage(msg) => {
            if let Page::Dashboard(page) = &mut model.page {
                page::dashboard::update(msg, page, &mut orders.proxy(Msg::DashboardPage))
            }
        }
        Msg::FsDashboardPage(msg) => {
            if let Page::FsDashboard(page) = &mut model.page {
                page::fs_dashboard::update(msg, page, &mut orders.proxy(Msg::FsDashboardPage))
            }
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
        Msg::Logout => {
            model.logging_out = true;

            orders.proxy(Msg::Auth).send_msg(Box::new(auth::Msg::Stop));

            orders.perform_cmd(
                auth::fetch_session()
                    .method(fetch::Method::Delete)
                    .fetch(Msg::LoggedOut),
            );
        }
        Msg::LoggedOut(_) => {
            orders.send_msg(Msg::GetSession);
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
        Msg::Login(msg) => {
            if let Page::Login(page) = &mut model.page {
                login::update(msg, page, &mut orders.proxy(Msg::Login));
            }
        }
        Msg::Auth(msg) => {
            if let (Some(_), Some(session)) = (model.auth.get_session(), model.loading.session.take()) {
                let _ = session.send(());
            }

            auth::update(*msg, &mut model.auth, &mut orders.proxy(|x| Msg::Auth(Box::new(x))));
        }
    }
}

fn handle_record_change(
    record_change: warp_drive::RecordChange,
    model: &mut Model,
    orders: &mut impl Orders<Msg, GMsg>,
) {
    match record_change {
        warp_drive::RecordChange::Update(record) => match record {
            warp_drive::Record::ActiveAlert(x) => {
                let msg = x.message.clone();

                model.records.active_alert.insert(x.id, Arc::new(x));

                let old = model.activity_health;

                model.activity_health = update_activity_health(&model.records.active_alert);
                orders.proxy(Msg::Notification).send_msg(notification::generate(
                    Some(msg),
                    &old,
                    &model.activity_health,
                ));
            }
            warp_drive::Record::Filesystem(x) => {
                let id = x.id;
                let fs = Arc::new(x);

                if model.records.filesystem.insert(id, Arc::clone(&fs)).is_none() {
                    orders
                        .proxy(Msg::Tree)
                        .send_msg(tree::Msg::Add(warp_drive::RecordId::Filesystem(id)));
                }

                orders
                    .proxy(Msg::FilesystemsPage)
                    .send_msg(page::filesystems::Msg::AddFilesystem(fs));
            }
            warp_drive::Record::ContentType(x) => {
                model.records.content_type.insert(x.id, Arc::new(x));
            }
            warp_drive::Record::Group(x) => {
                model.records.group.insert(x.id, Arc::new(x));
            }
            warp_drive::Record::Host(x) => {
                let id = x.id;
                if model.records.host.insert(x.id, Arc::new(x)).is_none() {
                    orders
                        .proxy(Msg::Tree)
                        .send_msg(tree::Msg::Add(warp_drive::RecordId::Host(id)));
                };

                orders.proxy(Msg::ServersPage).send_msg(page::servers::Msg::SetHosts(
                    model.records.host.arc_values().cloned().collect(),
                    model.records.lnet_configuration.clone(),
                ));

                orders
                    .proxy(Msg::FilesystemPage)
                    .proxy(page::filesystem::Msg::Stratagem)
                    .send_msg(stratagem::Msg::CheckStratagem);
            }
            warp_drive::Record::ManagedTargetMount(x) => {
                model.records.managed_target_mount.insert(x.id, Arc::new(x));
            }
            warp_drive::Record::OstPool(x) => {
                model.records.ost_pool.insert(x.id, Arc::new(x));
            }
            warp_drive::Record::OstPoolOsts(x) => {
                let id = x.id;
                if model.records.ost_pool_osts.insert(x.id, Arc::new(x)).is_none() {
                    orders
                        .proxy(Msg::Tree)
                        .send_msg(tree::Msg::Add(warp_drive::RecordId::OstPoolOsts(id)));
                };
            }
            warp_drive::Record::StratagemConfig(x) => {
                let x = Arc::new(x);

                model.records.stratagem_config.insert(x.id, Arc::clone(&x));

                orders
                    .proxy(Msg::FilesystemPage)
                    .proxy(page::filesystem::Msg::Stratagem)
                    .send_msg(stratagem::Msg::CheckStratagem);

                orders
                    .proxy(Msg::FilesystemPage)
                    .proxy(page::filesystem::Msg::Stratagem)
                    .send_msg(stratagem::Msg::UpdateStratagemConfig(x));
            }
            warp_drive::Record::Target(x) => {
                let id = x.id;
                let x = Arc::new(x);

                if model.records.target.insert(x.id, Arc::clone(&x)).is_none() {
                    orders
                        .proxy(Msg::Tree)
                        .send_msg(tree::Msg::Add(warp_drive::RecordId::Target(id)));
                };

                orders
                    .proxy(Msg::FilesystemPage)
                    .send_msg(page::filesystem::Msg::AddTarget(Arc::clone(&x)));

                orders
                    .proxy(Msg::TargetPage)
                    .send_msg(page::target::Msg::UpdateTarget(Arc::clone(&x)));

                orders.proxy(Msg::MgtsPage).send_msg(page::mgts::Msg::AddTarget(x));

                orders
                    .proxy(Msg::FilesystemPage)
                    .proxy(page::filesystem::Msg::Stratagem)
                    .send_msg(stratagem::Msg::CheckStratagem);
            }
            warp_drive::Record::User(x) => {
                model.records.user.insert(x.id, Arc::new(x));
            }
            warp_drive::Record::UserGroup(x) => {
                model.records.user_group.insert(x.id, Arc::new(x));
            }
            warp_drive::Record::Volume(x) => {
                model.records.volume.insert(x.id, Arc::new(x));
            }
            warp_drive::Record::VolumeNode(x) => {
                let id = x.id;
                if model.records.volume_node.insert(x.id, Arc::new(x)).is_none() {
                    orders
                        .proxy(Msg::Tree)
                        .send_msg(tree::Msg::Add(warp_drive::RecordId::VolumeNode(id)));
                };
            }
            warp_drive::Record::LnetConfiguration(x) => {
                model.records.lnet_configuration.insert(x.id, Arc::new(x));
            }
        },
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
                        .proxy(Msg::FilesystemPage)
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

pub fn main_panels(model: &Model, children: impl View<Msg>) -> impl View<Msg> {
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
                    children.els()
                ],
                page::partial::footer::view().els(),
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
    match &model.page {
        Page::AppLoading => loading::view().els(),
        Page::About => main_panels(model, page::about::view(model)).els(),
        Page::Dashboard(page) => main_panels(model, page::dashboard::view(page)).els(),
        Page::Filesystems(page) => main_panels(
            model,
            page::filesystems::view(&model.records, page, &model.locks, model.auth.get_session())
                .els()
                .map_msg(Msg::FilesystemsPage),
        )
        .els(),
        Page::Filesystem(page) => main_panels(
            model,
            page::filesystem::view(&model.records, page, &model.locks, model.auth.get_session())
                .els()
                .map_msg(Msg::FilesystemPage),
        )
        .els(),
        Page::ServerDashboard(page) => main_panels(model, page::server_dashboard::view(&model.records, page)).els(),
        Page::TargetDashboard(page) => main_panels(model, page::target_dashboard::view(&model.records, page)).els(),
        Page::FsDashboard(page) => main_panels(model, page::fs_dashboard::view(page)).els(),
        Page::Jobstats => main_panels(model, page::jobstats::view(model)).els(),
        Page::Login(x) => page::login::view(x).els().map_msg(Msg::Login),
        Page::Mgts(x) => main_panels(
            model,
            page::mgts::view(&model.records, x, &model.locks, model.auth.get_session())
                .els()
                .map_msg(Msg::MgtsPage),
        )
        .els(),
        Page::NotFound => page::not_found::view(model).els(),
        Page::OstPools => main_panels(model, page::ostpools::view(model)).els(),
        Page::OstPool(x) => main_panels(model, page::ostpool::view(x)).els(),
        Page::PowerControl => main_panels(model, page::power_control::view(model)).els(),
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
            .map_msg(Msg::ServersPage),
        )
        .els(),
        Page::Server(x) => main_panels(model, page::server::view(x)).els(),
        Page::Targets => main_panels(model, page::targets::view(model)).els(),
        Page::Target(x) => main_panels(
            model,
            page::target::view(&model.records, x, &model.locks, model.auth.get_session())
                .els()
                .map_msg(Msg::TargetPage),
        )
        .els(),
        Page::Users => main_panels(model, page::users::view(&model.records)).els(),
        Page::User(x) => main_panels(model, page::user::view(x)).els(),
        Page::Volumes => main_panels(model, page::volumes::view(model)).els(),
        Page::Volume(x) => main_panels(model, page::volume::view(x)).els(),
    }
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
