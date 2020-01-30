pub mod about;
pub mod activity;
pub mod dashboard;
pub mod filesystem;
pub mod filesystem_detail;
pub mod jobstats;
pub mod login;
pub mod logs;
pub mod mgt;
pub mod not_found;
pub mod ostpool;
pub mod ostpool_detail;
pub mod partial;
pub mod power_control;
pub mod server;
pub mod server_detail;
pub mod target;
pub mod target_detail;
pub mod user;
pub mod user_detail;
pub mod volume;
pub mod volume_detail;

use crate::{
    route::{Route, RouteId},
    GMsg, Msg,
};
use iml_wire_types::warp_drive::Cache;
use seed::prelude::Orders;

pub enum Page {
    About,
    Activity,
    AppLoading,
    Dashboard,
    Filesystem,
    FilesystemDetail(filesystem_detail::Model),
    Jobstats,
    Login(login::Model),
    Logs,
    Mgt,
    NotFound,
    OstPool,
    OstPoolDetail(ostpool_detail::Model),
    PowerControl,
    Server(server::Model),
    ServerDetail(server_detail::Model),
    Target,
    TargetDetail(target_detail::Model),
    User,
    UserDetail(user_detail::Model),
    Volume,
    VolumeDetail(volume_detail::Model),
}

impl Default for Page {
    fn default() -> Self {
        Page::NotFound
    }
}

impl<'a> From<&Route<'a>> for Page {
    fn from(route: &Route<'a>) -> Self {
        match route {
            Route::About => Page::About,
            Route::Activity => Page::Activity,
            Route::Dashboard => Page::Dashboard,
            Route::Filesystem => Page::Filesystem,
            Route::FilesystemDetail(id) => id
                .parse()
                .map(|id| Page::FilesystemDetail(filesystem_detail::Model { id }))
                .unwrap_or_default(),
            Route::Jobstats => Page::Jobstats,
            Route::Login => Page::Login(login::Model::default()),
            Route::Logs => Page::Logs,
            Route::Mgt => Page::Mgt,
            Route::NotFound => Page::NotFound,
            Route::OstPool => Page::OstPool,
            Route::OstPoolDetail(id) => id
                .parse()
                .map(|id| Page::OstPoolDetail(ostpool_detail::Model { id }))
                .unwrap_or_default(),
            Route::PowerControl => Page::PowerControl,
            Route::Server => Page::Server(server::Model::default()),
            Route::ServerDetail(id) => id
                .parse()
                .map(|id| Page::ServerDetail(server_detail::Model { id }))
                .unwrap_or_default(),
            Route::Target => Page::Target,
            Route::TargetDetail(id) => id
                .parse()
                .map(|id| Page::TargetDetail(target_detail::Model { id }))
                .unwrap_or_default(),
            Route::User => Page::User,
            Route::UserDetail(id) => id
                .parse()
                .map(|id| Page::UserDetail(user_detail::Model { id }))
                .unwrap_or_default(),
            Route::Volume => Page::Volume,
            Route::VolumeDetail(id) => id
                .parse()
                .map(|id| Page::VolumeDetail(volume_detail::Model { id }))
                .unwrap_or_default(),
        }
    }
}

impl Page {
    /// Is the given `Route` equivalent to the current page?
    pub fn is_active<'a>(&self, route: &Route<'a>) -> bool {
        match (route, self) {
            (Route::About, Page::About)
            | (Route::Activity, Page::Activity)
            | (Route::Dashboard, Page::Dashboard)
            | (Route::Filesystem, Page::Filesystem)
            | (Route::Jobstats, Page::Jobstats)
            | (Route::Login, Page::Login(_))
            | (Route::Logs, Page::Logs)
            | (Route::Mgt, Page::Mgt)
            | (Route::NotFound, Page::NotFound)
            | (Route::OstPool, Page::OstPool)
            | (Route::PowerControl, Page::PowerControl)
            | (Route::Server, Page::Server(_))
            | (Route::Target, Page::Target)
            | (Route::User, Page::User)
            | (Route::Volume, Page::Volume) => true,
            (Route::FilesystemDetail(route_id), Page::FilesystemDetail(filesystem_detail::Model { id }))
            | (Route::OstPoolDetail(route_id), Page::OstPoolDetail(ostpool_detail::Model { id }))
            | (Route::ServerDetail(route_id), Page::ServerDetail(server_detail::Model { id }))
            | (Route::TargetDetail(route_id), Page::TargetDetail(target_detail::Model { id }))
            | (Route::UserDetail(route_id), Page::UserDetail(user_detail::Model { id }))
            | (Route::VolumeDetail(route_id), Page::VolumeDetail(volume_detail::Model { id })) => {
                route_id == &RouteId::from(id)
            }
            _ => false,
        }
    }
    /// Initialize the page. This gives a chance to initialize data when a page is switched to.
    pub fn init(&self, cache: &Cache, orders: &mut impl Orders<Msg, GMsg>) {
        match self {
            Page::Server(_) => server::init(cache, &mut orders.proxy(Msg::ServerPage)),
            _ => {}
        };
    }
}
