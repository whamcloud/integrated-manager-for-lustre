pub mod about;
pub mod activity;
pub mod dashboard;
pub mod filesystem;
pub mod filesystems;
pub mod jobstats;
pub mod login;
pub mod logs;
pub mod mgt;
pub mod not_found;
pub mod ostpool;
pub mod ostpools;
pub mod partial;
pub mod power_control;
pub mod server;
pub mod servers;
pub mod target;
pub mod targets;
pub mod user;
pub mod users;
pub mod volume;
pub mod volumes;

use crate::{
    route::{Route, RouteId},
    GMsg, Msg,
};
use iml_wire_types::warp_drive::ArcCache;
use seed::prelude::Orders;

pub(crate) enum Page {
    About,
    Activity,
    AppLoading,
    Dashboard,
    Filesystems(filesystems::Model),
    Filesystem(filesystem::Model),
    Jobstats,
    Login(login::Model),
    Logs,
    Mgt,
    NotFound,
    OstPools,
    OstPool(ostpool::Model),
    PowerControl,
    Servers(servers::Model),
    Server(server::Model),
    Targets,
    Target(target::Model),
    Users,
    User(user::Model),
    Volumes,
    Volume(volume::Model),
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
            Route::Filesystems => Self::Filesystems(filesystems::Model::default()),
            Route::Filesystem(id) => id
                .parse()
                .map(|id| {
                    Self::Filesystem(filesystem::Model {
                        id,
                        ..filesystem::Model::default()
                    })
                })
                .unwrap_or_default(),
            Route::Jobstats => Self::Jobstats,
            Route::Login => Self::Login(login::Model::default()),
            Route::Logs => Self::Logs,
            Route::Mgt => Self::Mgt,
            Route::NotFound => Self::NotFound,
            Route::OstPools => Self::OstPools,
            Route::OstPool(id) => id
                .parse()
                .map(|id| Self::OstPool(ostpool::Model { id }))
                .unwrap_or_default(),
            Route::PowerControl => Self::PowerControl,
            Route::Servers => Self::Servers(servers::Model::default()),
            Route::Server(id) => id
                .parse()
                .map(|id| Self::Server(server::Model { id }))
                .unwrap_or_default(),
            Route::Targets => Self::Targets,
            Route::Target(id) => id
                .parse()
                .map(|id| Self::Target(target::Model { id }))
                .unwrap_or_default(),
            Route::Users => Self::Users,
            Route::User(id) => id.parse().map(|id| Self::User(user::Model { id })).unwrap_or_default(),
            Route::Volumes => Self::Volumes,
            Route::Volume(id) => id
                .parse()
                .map(|id| Self::Volume(volume::Model { id }))
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
            | (Route::Filesystems, Self::Filesystems(_))
            | (Route::Jobstats, Self::Jobstats)
            | (Route::Login, Self::Login(_))
            | (Route::Logs, Self::Logs)
            | (Route::Mgt, Self::Mgt)
            | (Route::NotFound, Self::NotFound)
            | (Route::OstPools, Self::OstPools)
            | (Route::PowerControl, Self::PowerControl)
            | (Route::Servers, Self::Servers(_))
            | (Route::Targets, Self::Targets)
            | (Route::Users, Self::Users)
            | (Route::Volumes, Self::Volumes) => true,
            (Route::Filesystem(route_id), Self::Filesystem(filesystem::Model { id, .. }))
            | (Route::OstPool(route_id), Self::OstPool(ostpool::Model { id }))
            | (Route::Server(route_id), Self::Server(server::Model { id }))
            | (Route::Target(route_id), Self::Target(target::Model { id }))
            | (Route::User(route_id), Self::User(user::Model { id }))
            | (Route::Volume(route_id), Self::Volume(volume::Model { id })) => route_id == &RouteId::from(id),
            _ => false,
        }
    }
    /// Initialize the page. This gives a chance to initialize data when a page is switched to.
    pub fn init(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        if let Self::Servers(_) = self {
            servers::init(cache, &mut orders.proxy(Msg::ServersPage))
        };

        if let Self::Filesystems(_) = self {
            filesystems::init(cache, &mut orders.proxy(Msg::FilesystemsPage))
        }

        if let Self::Filesystem(_) = self {
            filesystem::init(cache, &mut orders.proxy(Msg::FilesystemPage))
        }
    }
}
