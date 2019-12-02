// @TODO: uncomment once https://github.com/rust-lang/rust/issues/54726 stable
//#![rustfmt::skip::macros(class)]

#![allow(clippy::used_underscore_binding)]
#![allow(clippy::non_ascii_literal)]
#![allow(clippy::enum_glob_use)]

mod components;
mod generated;
mod page;

use components::{update_activity_health, ActivityHealth};
use generated::css_classes::C;
use iml_wire_types::{warp_drive, AlertSeverity};
use js_sys::Function;
use seed::{events::Listener, prelude::*, *};
use std::{cmp, collections::HashMap, mem};
use wasm_bindgen::JsCast;
use web_sys::{EventSource, MessageEvent};
use Visibility::*;

const TITLE_SUFFIX: &str = "IML";
const USER_AGENT_FOR_PRERENDERING: &str = "ReactSnap";
const STATIC_PATH: &str = "static";
const SLIDER_WIDTH_PX: u32 = 5;
const MAX_SIDE_PERCENTAGE: f32 = 35f32;

#[derive(Clone, Copy, Eq, PartialEq)]
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

#[derive(Debug, Copy, Clone)]
pub enum WatchState {
    Watching,
    Open,
    Close,
}

impl Default for WatchState {
    fn default() -> Self {
        WatchState::Close
    }
}

impl WatchState {
    pub fn is_open(self) -> bool {
        match self {
            WatchState::Open => true,
            _ => false,
        }
    }
    pub fn is_watching(self) -> bool {
        match self {
            WatchState::Watching => true,
            _ => false,
        }
    }
    pub fn should_update(self) -> bool {
        self.is_watching() || self.is_open()
    }
    pub fn update(&mut self) {
        match self {
            WatchState::Close => {
                mem::replace(self, WatchState::Watching);
            }
            WatchState::Watching => {
                mem::replace(self, WatchState::Open);
            }
            WatchState::Open => {
                mem::replace(self, WatchState::Close);
            }
        }
    }
}

// ------ ------
//     Model
// ------ ------

pub struct Model {
    pub page: Page,
    pub menu_visibility: Visibility,
    pub in_prerendering: bool,
    pub manage_menu_state: WatchState,
    pub track_slider: bool,
    pub side_width_percentage: f32,
    pub records: warp_drive::Cache,
    pub locks: warp_drive::Locks,
    pub activity_health: ActivityHealth,
}

#[derive(Clone, Copy, Eq, PartialEq)]
pub enum Page {
    About,
    Activity,
    Dashboard,
    Filesystem,
    FilesystemDetail,
    Home,
    Jobstats,
    Login,
    Logs,
    Mgt,
    NotFound,
    PowerControl,
    Server,
    ServerDetail,
    Target,
    User,
    Volume,
}

impl Page {
    pub fn to_href(self) -> &'static str {
        match self {
            Self::About => "/about",
            Self::Activity => "/activity",
            Self::Dashboard => "/dashboard",
            Self::Filesystem => "/filesystem",
            Self::FilesystemDetail => "/filesystem_detail",
            Self::Home => "/",
            Self::Jobstats => "/jobstats",
            Self::Login => "/login",
            Self::Logs => "/logs",
            Self::Mgt => "/mgt",
            Self::NotFound => "/404",
            Self::PowerControl => "/power_control",
            Self::Server => "/server",
            Self::ServerDetail => "/server_detail",
            Self::Target => "/target",
            Self::User => "/user",
            Self::Volume => "/volume",
        }
    }
}

impl ToString for Page {
    fn to_string(&self) -> String {
        match self {
            Self::About => "About".into(),
            Self::Activity => "Activity".into(),
            Self::Dashboard => "Dashboard".into(),
            Self::Filesystem => "Filesystem".into(),
            Self::FilesystemDetail => "Filesystem Detail".into(),
            Self::Home => "Home".into(),
            Self::Jobstats => "Jobstats".into(),
            Self::Login => "Login".into(),
            Self::Logs => "Logs".into(),
            Self::Mgt => "Mgt".into(),
            Self::NotFound => "404".into(),
            Self::PowerControl => "Power Control".into(),
            Self::Server => "Server".into(),
            Self::ServerDetail => "Server Detail".into(),
            Self::Target => "Target".into(),
            Self::User => "User".into(),
            Self::Volume => "Volume".into(),
        }
    }
}

impl From<Url> for Page {
    fn from(url: Url) -> Self {
        match url.path.first().map(String::as_str) {
            Some("about") => Self::About,
            Some("activity") => Self::Activity,
            Some("dashboard") => Self::Dashboard,
            Some("filesystem") => Self::Filesystem,
            Some("filesystem_detail") => Self::FilesystemDetail,
            None | Some("") => Self::Home,
            Some("jobstats") => Self::Jobstats,
            Some("login") => Self::Login,
            Some("logs") => Self::Logs,
            Some("mgt") => Self::Mgt,
            Some("power_control") => Self::PowerControl,
            Some("server") => Self::Server,
            Some("server_detail") => Self::ServerDetail,
            Some("target") => Self::Target,
            Some("user") => Self::User,
            Some("volume") => Self::Volume,
            _ => Self::NotFound,
        }
    }
}

pub fn register_eventsource_handle<T, F>(
    es_cb_setter: fn(&EventSource, Option<&Function>),
    msg: F,
    ws: &EventSource,
    orders: &mut impl Orders<Msg>,
) where
    T: wasm_bindgen::convert::FromWasmAbi + 'static,
    F: Fn(T) -> Msg + 'static,
{
    let (app, msg_mapper) = (orders.clone_app(), orders.msg_mapper());

    let closure = Closure::new(move |data| {
        app.update(msg_mapper(msg(data)));
    });

    es_cb_setter(ws, Some(closure.as_ref().unchecked_ref()));
    closure.forget();
}

// ------ ------
//     Init
// ------ ------

pub fn init(url: Url, orders: &mut impl Orders<Msg>) -> Init<Model> {
    // @TODO: Seed can't hydrate prerendered html (yet).
    // https://github.com/David-OConnor/seed/issues/223
    if let Some(mount_point_element) = document().get_element_by_id("app") {
        mount_point_element.set_inner_html("");
    }

    let es = EventSource::new("https://localhost:7444/messaging").unwrap();

    register_eventsource_handle(
        EventSource::set_onopen,
        Msg::EventSourceConnect,
        &es,
        orders,
    );

    register_eventsource_handle(
        EventSource::set_onmessage,
        Msg::EventSourceMessage,
        &es,
        orders,
    );

    register_eventsource_handle(
        EventSource::set_onerror,
        Msg::EventSourceError,
        &es,
        orders,
    );

    orders.send_msg(Msg::UpdatePageTitle);

    Init::new(Model {
        page: url.into(),
        menu_visibility: Visible,
        in_prerendering: is_in_prerendering(),
        manage_menu_state: WatchState::default(),
        track_slider: false,
        side_width_percentage: 20f32,
        records: warp_drive::Cache::default(),
        locks: HashMap::new(),
        activity_health: ActivityHealth {
            count: 0,
            health: AlertSeverity::INFO,
        },
    })
}

fn is_in_prerendering() -> bool {
    let user_agent =
        window().navigator().user_agent().expect("cannot get user agent");

    user_agent == USER_AGENT_FOR_PRERENDERING
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
//    Update
// ------ ------

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
    Records(warp_drive::Cache),
    RecordChange(warp_drive::RecordChange),
    Locks(warp_drive::Locks),
    WindowClick,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::RouteChanged(url) => {
            model.page = url.into();
            orders.send_msg(Msg::UpdatePageTitle);
        }
        Msg::UpdatePageTitle => {
            let title =
                format!("{} - {}", model.page.to_string(), TITLE_SUFFIX);

            document().set_title(&title);
        }
        Msg::EventSourceConnect(_) => {
            log("EventSource connected.");
        }
        Msg::EventSourceMessage(msg) => {
            let txt = msg.data().as_string().unwrap();

            let msg: warp_drive::Message = serde_json::from_str(&txt).unwrap();

            let msg = match msg {
                warp_drive::Message::Locks(locks) => Msg::Locks(locks),
                warp_drive::Message::Records(records) => Msg::Records(records),
                warp_drive::Message::RecordChange(record_change) => {
                    Msg::RecordChange(record_change)
                }
            };

            orders.send_msg(msg);
        }
        Msg::EventSourceError(_) => {
            log("EventSource error.");
        }
        Msg::Records(records) => {
            model.records = records;

            model.activity_health =
                update_activity_health(&model.records.active_alert);
        }
        Msg::RecordChange(record_change) => match record_change {
            warp_drive::RecordChange::Update(record) => match record {
                warp_drive::Record::ActiveAlert(x) => {
                    model.records.active_alert.insert(x.id, x);

                    model.activity_health =
                        update_activity_health(&model.records.active_alert);
                }
                warp_drive::Record::Filesystem(x) => {
                    model.records.filesystem.insert(x.id, x);
                }
                warp_drive::Record::Host(x) => {
                    model.records.host.insert(x.id, x);
                }
                warp_drive::Record::ManagedTargetMount(x) => {
                    model.records.managed_target_mount.insert(x.id, x);
                }
                warp_drive::Record::StratagemConfig(x) => {
                    model.records.stratagem_config.insert(x.id, x);
                }
                warp_drive::Record::Target(x) => {
                    model.records.target.insert(x.id, x);
                }
                warp_drive::Record::Volume(x) => {
                    model.records.volume.insert(x.id, x);
                }
                warp_drive::Record::VolumeNode(x) => {
                    model.records.volume_node.insert(x.id, x);
                }
                warp_drive::Record::LnetConfiguration(x) => {
                    model.records.lnet_configuration.insert(x.id, x);
                }
            },
            warp_drive::RecordChange::Delete(record_id) => match record_id {
                warp_drive::RecordId::ActiveAlert(x) => {
                    model.records.active_alert.remove(&x);
                }
                warp_drive::RecordId::Filesystem(x) => {
                    model.records.filesystem.remove(&x);
                }
                warp_drive::RecordId::Host(x) => {
                    model.records.host.remove(&x);
                }
                warp_drive::RecordId::ManagedTargetMount(x) => {
                    model.records.managed_target_mount.remove(&x);
                }
                warp_drive::RecordId::StratagemConfig(x) => {
                    model.records.stratagem_config.remove(&x);
                }
                warp_drive::RecordId::Target(x) => {
                    model.records.target.remove(&x);
                }
                warp_drive::RecordId::Volume(x) => {
                    model.records.volume.remove(&x);
                }
                warp_drive::RecordId::VolumeNode(x) => {
                    model.records.volume_node.remove(&x);
                }
                warp_drive::RecordId::LnetConfiguration(x) => {
                    model.records.lnet_configuration.remove(&x);
                }
            },
        },
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

            let side_width_percentage: f32 =
                (x_position as f32 / overlay_width_px as f32) * 100_f32;

            model.side_width_percentage =
                if MAX_SIDE_PERCENTAGE <= side_width_percentage {
                    MAX_SIDE_PERCENTAGE
                } else {
                    side_width_percentage
                };
        }
        Msg::WindowClick => {
            if model.manage_menu_state.should_update() {
                model.manage_menu_state.update();
            }
        }
    }
}

// ------ ------
//     View
// ------ ------

// Notes:
// - \u{00A0} is the non-breaking space
//   - https://codepoints.net/U+00A0
//
// - "▶\u{fe0e}" - \u{fe0e} is the variation selector, it prevents ▶ to change to emoji in some browsers
//   - https://codepoints.net/U+FE0E

pub fn view(model: &Model) -> impl View<Msg> {
    // @TODO: Setup `prerendered` properly once https://github.com/David-OConnor/seed/issues/223 is resolved
    let prerendered = true;

    div![
        class![
            C.fade_in => !prerendered,
            C.min_h_screen,
            C.flex,
            C.flex_col,
            C.select_none => model.track_slider
        ],
        // slider overlay
        if model.track_slider {
            div![
                class![
                    C.w_full,
                    C.h_full,
                    C.fixed,
                    C.top_0,
                    C.cursor_ew_resize,
                ],
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
            class![
                C.flex,
                C.flex_wrap,
                C.flex_col,
                C.lg__flex_row,
                C.flex_grow
            ],
            // side panel
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
            ],
            // slider panel
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
            ],
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
                    class![
                        C.flex_grow,
                        C.overflow_x_auto,
                        C.overflow_y_auto,
                        C.p_6
                    ],
                    match model.page {
                        Page::About => page::about::view(&model).els(),
                        Page::Activity => page::activity::view(&model).els(),
                        Page::Dashboard => page::dashboard::view(&model).els(),
                        Page::Filesystem =>
                            page::filesystem::view(&model).els(),
                        Page::FilesystemDetail =>
                            page::filesystem_detail::view(&model).els(),
                        Page::Home => page::home::view(&model).els(),
                        Page::Jobstats => page::jobstats::view(&model).els(),
                        Page::Login => page::login::view(&model).els(),
                        Page::Logs => page::logs::view(&model).els(),
                        Page::Mgt => page::mgt::view(&model).els(),
                        Page::NotFound => page::not_found::view(&model).els(),
                        Page::PowerControl =>
                            page::power_control::view(&model).els(),
                        Page::Server => page::server::view(&model).els(),
                        Page::ServerDetail =>
                            page::server_detail::view(&model).els(),
                        Page::Target => page::target::view(&model).els(),
                        Page::User => page::user::view(&model).els(),
                        Page::Volume => page::volume::view(&model).els(),
                    },
                ],
                page::partial::footer::view().els(),
            ]
        ],
    ]
}

pub fn asset_path(asset: &str) -> String {
    format!("{}/{}", STATIC_PATH, asset)
}

// ------ ------
// Window Events
// ------ ------

pub fn window_events(model: &Model) -> Vec<Listener<Msg>> {
    let mut xs = vec![simple_ev(Ev::Click, Msg::WindowClick)];

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

    App::build(init, update, view)
        .routes(routes)
        .window_events(window_events)
        .finish()
        .run();

    log!("App started.");
}
