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
use iml_wire_types::warp_drive::ArcCache;
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
        Self::NotFound
    }
}

impl<'a> From<&Route<'a>> for Page {
    fn from(route: &Route<'a>) -> Self {
        match route {
            Route::About => Self::About,
            Route::Activity => Self::Activity,
            Route::Dashboard => Self::Dashboard,
            Route::Filesystem => Self::Filesystem,
            Route::FilesystemDetail(id) => id
                .parse()
                .map(|id| Self::FilesystemDetail(filesystem_detail::Model { id }))
                .unwrap_or_default(),
            Route::Jobstats => Self::Jobstats,
            Route::Login => Self::Login(login::Model::default()),
            Route::Logs => Self::Logs,
            Route::Mgt => Self::Mgt,
            Route::NotFound => Self::NotFound,
            Route::OstPool => Self::OstPool,
            Route::OstPoolDetail(id) => id
                .parse()
                .map(|id| Self::OstPoolDetail(ostpool_detail::Model { id }))
                .unwrap_or_default(),
            Route::PowerControl => Self::PowerControl,
            Route::Server => Self::Server(server::Model::default()),
            Route::ServerDetail(id) => id
                .parse()
                .map(|id| Self::ServerDetail(server_detail::Model { id }))
                .unwrap_or_default(),
            Route::Target => Self::Target,
            Route::TargetDetail(id) => id
                .parse()
                .map(|id| Self::TargetDetail(target_detail::Model { id }))
                .unwrap_or_default(),
            Route::User => Self::User,
            Route::UserDetail(id) => id
                .parse()
                .map(|id| Self::UserDetail(user_detail::Model { id }))
                .unwrap_or_default(),
            Route::Volume => Self::Volume,
            Route::VolumeDetail(id) => id
                .parse()
                .map(|id| Self::VolumeDetail(volume_detail::Model { id }))
                .unwrap_or_default(),
        }
    }
}

impl Page {
    /// Is the given `Route` equivalent to the current page?
    pub fn is_active<'a>(&self, route: &Route<'a>) -> bool {
        match (route, self) {
            (Route::About, Self::About)
            | (Route::Activity, Self::Activity)
            | (Route::Dashboard, Self::Dashboard)
            | (Route::Filesystem, Self::Filesystem)
            | (Route::Jobstats, Self::Jobstats)
            | (Route::Login, Self::Login(_))
            | (Route::Logs, Self::Logs)
            | (Route::Mgt, Self::Mgt)
            | (Route::NotFound, Self::NotFound)
            | (Route::OstPool, Self::OstPool)
            | (Route::PowerControl, Self::PowerControl)
            | (Route::Server, Self::Server(_))
            | (Route::Target, Self::Target)
            | (Route::User, Self::User)
            | (Route::Volume, Self::Volume) => true,
            (Route::FilesystemDetail(route_id), Self::FilesystemDetail(filesystem_detail::Model { id }))
            | (Route::OstPoolDetail(route_id), Self::OstPoolDetail(ostpool_detail::Model { id }))
            | (Route::ServerDetail(route_id), Self::ServerDetail(server_detail::Model { id }))
            | (Route::TargetDetail(route_id), Self::TargetDetail(target_detail::Model { id }))
            | (Route::UserDetail(route_id), Self::UserDetail(user_detail::Model { id }))
            | (Route::VolumeDetail(route_id), Self::VolumeDetail(volume_detail::Model { id })) => {
                route_id == &RouteId::from(id)
            }
            _ => false,
        }
    }
    /// Initialize the page. This gives a chance to initialize data when a page is switched to.
    pub fn init(&self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        if let Self::Server(_) = self {
            server::init(cache, &mut orders.proxy(Msg::ServerPage))
        };
    }
}
