#![allow(clippy::used_underscore_binding)]
#![allow(clippy::non_ascii_literal)]
#![allow(clippy::enum_glob_use)]

pub mod components;
pub mod key_codes;

mod auth;
mod breakpoints;
mod ctx_help;
mod event_source;
mod extensions;
mod generated;
mod notification;
mod page;
mod route;
mod sleep;
mod watch_state;

#[cfg(test)]
mod test_utils;

use components::{breadcrumbs::BreadCrumbs, loading, restrict, tree, update_activity_health, ActivityHealth};
pub(crate) use extensions::*;
use generated::css_classes::C;
use iml_wire_types::{warp_drive, GroupType, Session};
use page::login;
use regex::Regex;
use route::Route;
use seed::{app::MessageMapper, prelude::*, Listener, *};
pub(crate) use sleep::sleep_with_handle;
use std::cmp;
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
const CTX_HELP: &str = "help/docs/Graphical_User_Interface_9_0.html";

pub fn extract_api(s: &str) -> Option<&str> {
    let re = Regex::new(r"^/?api/[^/]+/(\d+)/?$").unwrap();

    let x = re.captures(s)?;

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

// ------ ------
//     Model
// ------ ------

pub struct Model {
    activity_health: ActivityHealth,
    auth: auth::Model,
    breadcrumbs: BreadCrumbs<Route<'static>>,
    breakpoint_size: breakpoints::Size,
    locks: warp_drive::Locks,
    logging_out: bool,
    login: login::Model,
    manage_menu_state: WatchState,
    menu_visibility: Visibility,
    notification: notification::Model,
    records: warp_drive::Cache,
    route: Route<'static>,
    saw_es_locks: bool,
    saw_es_messages: bool,
    server_page: page::server::Model,
    side_width_percentage: f32,
    track_slider: bool,
    tree: tree::Model,
}

impl Model {
    /// Do we have enough data to load the app?
    fn loaded(&self) -> bool {
        self.auth.get_session().is_some() && self.saw_es_messages && self.saw_es_locks
    }
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

    orders.proxy(Msg::Auth).send_msg(auth::Msg::Fetch);

    AfterMount::new(Model {
        activity_health: ActivityHealth::default(),
        auth: auth::Model::default(),
        breadcrumbs: BreadCrumbs::default(),
        breakpoint_size: breakpoints::size(),
        locks: im::hashmap!(),
        logging_out: false,
        login: login::Model::default(),
        manage_menu_state: WatchState::default(),
        menu_visibility: Visible,
        notification: notification::Model::default(),
        records: warp_drive::Cache::default(),
        route: url.into(),
        saw_es_locks: false,
        saw_es_messages: false,
        server_page: page::server::Model::default(),
        side_width_percentage: 20_f32,
        track_slider: false,
        tree: tree::Model::default(),
    })
}

// ------ ------
//    Routes
// ------ ------

pub fn routes(url: Url) -> Option<Msg> {
    // Urls which start with `static` are files => treat them as external links.
    if url.path.starts_with(&[STATIC_PATH.into()]) {
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
    AuthProxy(auth::Msg),
}

fn sink(g_msg: GMsg, _model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match g_msg {
        GMsg::RouteChange(url) => {
            seed::push_route(url.clone());
            orders.send_msg(Msg::RouteChanged(url));
        }
        GMsg::AuthProxy(msg) => {
            orders.proxy(Msg::Auth).send_msg(msg);
        }
    }
}

// ------ ------
//    Update
// ------ ------

#[allow(clippy::large_enum_variant)]
#[derive(Clone)]
pub enum Msg {
    RouteChanged(Url),
    UpdatePageTitle,
    ToggleMenu,
    ManageMenuState,
    HideMenu,
    StartSliderTracking,
    StopSliderTracking,
    SliderX(i32, f64),
    EventSourceConnect(JsValue),
    EventSourceMessage(MessageEvent),
    EventSourceError(JsValue),
    Records(Box<warp_drive::Cache>),
    RecordChange(Box<warp_drive::RecordChange>),
    RemoveRecord(warp_drive::RecordId),
    Locks(warp_drive::Locks),
    ServerPage(page::server::Msg),
    WindowClick,
    WindowResize,
    Notification(notification::Msg),
    GetSession,
    GotSession(fetch::ResponseDataResult<Session>),
    Login(login::Msg),
    Logout,
    LoggedOut(fetch::FetchObject<()>),
    Tree(tree::Msg),
    Auth(auth::Msg),
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
        }
        Msg::UpdatePageTitle => {
            let title = format!("{} - {}", model.route.to_string(), TITLE_SUFFIX);

            document().set_title(&title);
        }
        Msg::EventSourceConnect(_) => {
            log("EventSource connected.");
        }
        Msg::EventSourceMessage(msg) => {
            let txt = msg.data().as_string().unwrap();

            let msg: warp_drive::Message = serde_json::from_str(&txt).unwrap();

            let msg = match msg {
                warp_drive::Message::Locks(locks) => {
                    model.saw_es_locks = true;

                    Msg::Locks(locks)
                }
                warp_drive::Message::Records(records) => {
                    model.saw_es_messages = true;

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
                orders.send_g_msg(GMsg::AuthProxy(auth::Msg::SetSession(resp)));

                model.logging_out = false;
            }
            Err(fail_reason) => {
                error!("Error fetching login session {:?}", fail_reason.message());

                orders.skip();
            }
        },
        Msg::Records(records) => {
            model.records = *records;

            let old = model.activity_health;
            model.activity_health = update_activity_health(&model.records.active_alert);

            orders
                .proxy(Msg::Notification)
                .send_msg(notification::generate(None, &old, &model.activity_health));

            orders.proxy(Msg::ServerPage).send_msg(page::server::Msg::SetHosts(
                model.records.host.values().cloned().collect(),
            ));

            orders.proxy(Msg::Tree).send_msg(tree::Msg::Reset);
        }
        Msg::RecordChange(record_change) => match *record_change {
            warp_drive::RecordChange::Update(record) => match record {
                warp_drive::Record::ActiveAlert(x) => {
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
                warp_drive::Record::Filesystem(x) => {
                    let id = x.id;
                    if model.records.filesystem.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::Filesystem(id)));
                    };
                }
                warp_drive::Record::Host(x) => {
                    let id = x.id;
                    if model.records.host.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::Host(id)));
                    };

                    orders.proxy(Msg::ServerPage).send_msg(page::server::Msg::SetHosts(
                        model.records.host.values().cloned().collect(),
                    ));
                }
                warp_drive::Record::ManagedTargetMount(x) => {
                    model.records.managed_target_mount.insert(x.id, x);
                }
                warp_drive::Record::OstPool(x) => {
                    model.records.ost_pool.insert(x.id, x);
                }
                warp_drive::Record::OstPoolOsts(x) => {
                    let id = x.id;
                    if model.records.ost_pool_osts.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::OstPoolOsts(id)));
                    };
                }
                warp_drive::Record::StratagemConfig(x) => {
                    model.records.stratagem_config.insert(x.id, x);
                }
                warp_drive::Record::Target(x) => {
                    let id = x.id;
                    if model.records.target.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::Target(id)));
                    };
                }
                warp_drive::Record::Volume(x) => {
                    model.records.volume.insert(x.id, x);
                }
                warp_drive::Record::VolumeNode(x) => {
                    let id = x.id;
                    if model.records.volume_node.insert(x.id, x).is_none() {
                        orders
                            .proxy(Msg::Tree)
                            .send_msg(tree::Msg::Add(warp_drive::RecordId::VolumeNode(id)));
                    };
                }
                warp_drive::Record::LnetConfiguration(x) => {
                    model.records.lnet_configuration.insert(x.id, x);
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
                    _ => {}
                };

                orders.send_msg(Msg::RemoveRecord(record_id));
            }
        },
        Msg::RemoveRecord(id) => {
            model.records.remove_record(&id);

            if let warp_drive::RecordId::Host(_) = id {
                orders.proxy(Msg::ServerPage).send_msg(page::server::Msg::SetHosts(
                    model.records.host.values().cloned().collect(),
                ));
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
        Msg::ServerPage(msg) => page::server::update(msg, &mut model.server_page, &mut orders.proxy(Msg::ServerPage)),
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
        Msg::Logout => {
            model.logging_out = true;

            orders.proxy(Msg::Auth).send_msg(auth::Msg::Stop);

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

            orders.proxy(Msg::ServerPage).send_msg(page::server::Msg::WindowClick);
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
            login::update(msg, &mut model.login, &mut orders.proxy(Msg::Login));
        }
        Msg::Auth(msg) => {
            auth::update(msg, &mut model.auth, &mut orders.proxy(Msg::Auth));
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
                        C.bg_blue_900,
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
                        C.flex_grow_0,
                        C.flex_shrink_0,
                        C.cursor_ew_resize,
                        C.bg_gray_500
                        C.hover__bg_teal_400,
                        C.bg_teal_400 => model.track_slider,
                        C.relative,
                        C.lg__block,
                        C.lg__h_main_content,
                        C.hidden
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
                    C.bg_gray_200,
                    C.lg__w_0,
                    C.lg__h_main_content,
                ],
                // main content
                div![
                    class![C.flex_grow, C.overflow_x_auto, C.overflow_y_auto, C.p_6],
                    children.els()
                ],
                page::partial::footer::view().els(),
            ]
        ],
    ]
}

pub fn view(model: &Model) -> Vec<Node<Msg>> {
    if !model.loaded() {
        return loading::view().els();
    }

    match &model.route {
        Route::About => main_panels(model, page::about::view(model)).els(),
        Route::Activity => main_panels(model, page::activity::view(model)).els(),
        Route::Dashboard => main_panels(model, page::dashboard::view(model)).els(),
        Route::Filesystem => main_panels(model, page::filesystem::view(model)).els(),
        Route::FilesystemDetail(id) => main_panels(model, page::filesystem_detail::view(model, id)).els(),
        Route::Jobstats => main_panels(model, page::jobstats::view(model)).els(),
        Route::Login => page::login::view(&model.login).els().map_msg(Msg::Login),
        Route::Logs => main_panels(model, page::logs::view(model)).els(),
        Route::Mgt => main_panels(model, page::mgt::view(model)).els(),
        Route::NotFound => page::not_found::view(model).els(),
        Route::OstPool => main_panels(model, page::ostpool::view(model)).els(),
        Route::OstPoolDetail(id) => main_panels(model, page::ostpool_detail::view(model, id)).els(),
        Route::PowerControl => main_panels(model, page::power_control::view(model)).els(),
        Route::Server => main_panels(
            model,
            page::server::view(&model.records, &model.server_page)
                .els()
                .map_msg(Msg::ServerPage),
        )
        .els(),
        Route::ServerDetail(id) => main_panels(model, page::server_detail::view(model, id)).els(),
        Route::Target => main_panels(model, page::target::view(model)).els(),
        Route::TargetDetail(id) => main_panels(model, page::target_detail::view(model, id)).els(),
        Route::User => main_panels(model, page::user::view(model)).els(),
        Route::UserDetail(id) => main_panels(model, page::user_detail::view(model, id)).els(),
        Route::Volume => main_panels(model, page::volume::view(model)).els(),
        Route::VolumeDetail(id) => main_panels(model, page::volume_detail::view(model, id)).els(),
    }
}

pub fn asset_path(asset: &str) -> String {
    format!("{}/{}", STATIC_PATH, asset)
}

// ------ ------
// Window Events
// ------ ------

pub fn window_events(model: &Model) -> Vec<Listener<Msg>> {
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
