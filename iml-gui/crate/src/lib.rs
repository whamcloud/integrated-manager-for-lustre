// @TODO: uncomment once https://github.com/rust-lang/rust/issues/54726 stable
//#![rustfmt::skip::macros(class)]

#![allow(clippy::used_underscore_binding)]
#![allow(clippy::non_ascii_literal)]
#![allow(clippy::enum_glob_use)]

mod generated;
mod page;

use generated::css_classes::C;
use seed::{events::Listener, prelude::*, *};
use std::mem;
use web_sys::EventSource;
use Visibility::*;

const TITLE_SUFFIX: &str = "IML";
const USER_AGENT_FOR_PRERENDERING: &str = "ReactSnap";
const STATIC_PATH: &str = "static";
const IMAGES_PATH: &str = "static/images";

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
    pub config_menu_state: WatchState,
    pub track_slider: bool,
}

#[derive(Clone, Copy, Eq, PartialEq)]
pub enum Page {
    Dashboard,
    Home,
    About,
    NotFound,
}

impl Page {
    pub fn to_href(self) -> &'static str {
        match self {
            Self::Dashboard => "/dashboard",
            Self::Home => "/",
            Self::About => "/about",
            Self::NotFound => "/404",
        }
    }
}

impl ToString for Page {
    fn to_string(&self) -> String {
        match self {
            Self::Dashboard => "Dashboard".into(),
            Self::Home => "Home".into(),
            Self::About => "About".into(),
            Self::NotFound => "404".into(),
        }
    }
}

impl From<Url> for Page {
    fn from(url: Url) -> Self {
        match url.path.first().map(String::as_str) {
            None | Some("") => Self::Home,
            Some("dashboard") => Self::Dashboard,
            Some("about") => Self::About,
            _ => Self::NotFound,
        }
    }
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

    let es = EventSource::new("https://localhost:7444/messaging");

    orders.send_msg(Msg::UpdatePageTitle);

    Init::new(Model {
        page: url.into(),
        menu_visibility: Visible,
        in_prerendering: is_in_prerendering(),
        config_menu_state: WatchState::default(),
        track_slider: false,
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
    ConfigMenuState,
    HideMenu,
    StartSliderTracking,
    StopSliderTracking,
    SliderX(i32),
    WindowClick,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::RouteChanged(url) => {
            model.page = url.into();
            orders.send_msg(Msg::UpdatePageTitle);
        }
        Msg::UpdatePageTitle => {
            let title = match model.page {
                Page::Home => TITLE_SUFFIX.to_owned(),
                Page::Dashboard => format!("Dashboard - {}", TITLE_SUFFIX),
                Page::About => format!("About - {}", TITLE_SUFFIX),
                Page::NotFound => format!("404 - {}", TITLE_SUFFIX),
            };
            document().set_title(&title);
        }
        Msg::ToggleMenu => model.menu_visibility.toggle(),
        Msg::ConfigMenuState => {
            model.config_menu_state.update();
        }
        Msg::HideMenu => {
            model.menu_visibility = Hidden;
        }
        Msg::StartSliderTracking => {
            model.track_slider = true;

            orders.skip();
        }
        Msg::StopSliderTracking => {
            model.track_slider = false;

            orders.skip();
        }
        Msg::SliderX(x) => {
            log(format!("{}", x));
        }
        Msg::WindowClick => {
            if model.config_menu_state.should_update() {
                model.config_menu_state.update();
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
            C.flex_col
        ],
        page::partial::header::view(model).els(),
        // panel container
        div![
            class![
                C.flex,
                C.flex_wrap,
                C.flex_col,
                C.lg__flex_row,
                C.min_h_screen,
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
                    C.border_gray_800
                ],
                style! { St::FlexBasis => percent(20) },
            ],
            // slider panel
            div![
                class![
                    C.flex_grow_0,
                    C.flex_shrink_0,
                    C.cursor_ew_resize,
                    C.bg_gray_500
                    C.hover__bg_teal_400,
                    C.relative,
                ],
                simple_ev(Ev::MouseDown, Msg::StartSliderTracking),
                style! {
                    St::FlexBasis => px(5),
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
                    C.bg_gray_200
                ],
                style! { "flex-basis" => 0},
                match model.page {
                    Page::Home => page::home::view(&model).els(),
                    Page::Dashboard => page::dashboard::view(&model).els(),
                    Page::About => page::about::view(&model).els(),
                    Page::NotFound => page::not_found::view(&model).els(),
                },
                page::partial::footer::view().els(),
            ]
        ],
    ]
}

pub fn image_src(image: &str) -> String {
    format!("{}/{}", IMAGES_PATH, image)
}

pub fn asset_path(asset: &str) -> String {
    format!("{}/{}", STATIC_PATH, asset)
}

// ------ ------
// Window Events
// ------ ------

pub fn window_events(model: &Model) -> Vec<Listener<Msg>> {
    log!("calling window_events");

    let mut xs = vec![simple_ev(Ev::Click, Msg::WindowClick)];

    if model.track_slider {
        xs.push(mouse_ev(Ev::MouseMove, |ev| Msg::SliderX(ev.client_x())));
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
