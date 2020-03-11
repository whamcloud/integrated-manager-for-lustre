pub mod about;
pub mod activity;
pub mod dashboard;
pub mod filesystem;
pub mod filesystems;
pub mod fs_dashboard;
pub mod jobstats;
pub mod login;
pub mod logs;
pub mod mgts;
pub mod not_found;
pub mod ostpool;
pub mod ostpools;
pub mod partial;
pub mod power_control;
pub mod server;
pub mod server_dashboard;
pub mod servers;
pub mod target;
pub mod target_dashboard;
pub mod targets;
pub mod user;
pub mod users;
pub mod volume;
pub mod volumes;

use crate::{
    components::stratagem,
    route::{Route, RouteId},
    GMsg, Msg,
};
use iml_wire_types::warp_drive::ArcCache;
use seed::prelude::Orders;
use std::sync::Arc;

pub(crate) enum Page {
    About,
    AppLoading,
    Filesystems(filesystems::Model),
    Filesystem(Box<filesystem::Model>),
    Dashboard(dashboard::Model),
    FsDashboard(fs_dashboard::Model),
    ServerDashboard(server_dashboard::Model),
    TargetDashboard(target_dashboard::Model),
    Jobstats,
    Login(login::Model),
    Mgts(mgts::Model),
    NotFound,
    OstPools,
    OstPool(ostpool::Model),
    PowerControl,
    Servers(servers::Model),
    Server(server::Model),
    Targets,
    Target(Box<target::Model>),
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

impl<'a> From<(&ArcCache, &Route<'a>)> for Page {
    fn from((cache, route): (&ArcCache, &Route<'a>)) -> Self {
        match route {
            Route::About => Self::About,
            Route::Filesystems => Self::Filesystems(filesystems::Model::default()),
            Route::Filesystem(id) => id
                .parse()
                .ok()
                .and_then(|x| cache.filesystem.get(&x))
                .map(|x| {
                    Self::Filesystem(Box::new(filesystem::Model {
                        fs: Arc::clone(x),
                        mdts: Default::default(),
                        mdt_paging: Default::default(),
                        mgt: Default::default(),
                        osts: Default::default(),
                        ost_paging: Default::default(),
                        rows: Default::default(),
                        stratagem: stratagem::Model::new(Arc::clone(x)),
                    }))
                })
                .unwrap_or_default(),
            Route::Dashboard => Self::Dashboard(dashboard::Model {
                ..dashboard::Model::default()
            }),
            Route::FsDashboard(id) => Self::FsDashboard(fs_dashboard::Model {
                fs_name: id.to_string(),
                ..fs_dashboard::Model::default()
            }),
            Route::ServerDashboard(id) => Self::ServerDashboard(server_dashboard::Model {
                host_name: id.to_string(),
            }),
            Route::TargetDashboard(id) => Self::TargetDashboard(target_dashboard::Model {
                target_name: id.to_string(),
            }),
            Route::Jobstats => Self::Jobstats,
            Route::Login => Self::Login(login::Model::default()),
            Route::Mgt => Self::Mgts(mgts::Model::default()),
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
                .ok()
                .and_then(|x| cache.target.get(&x))
                .map(|x| Self::Target(Box::new(target::Model::new(Arc::clone(x)))))
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
            | (Route::Filesystems, Self::Filesystems(_))
            | (Route::Dashboard, Self::Dashboard(dashboard::Model { .. }))
            | (Route::Jobstats, Self::Jobstats)
            | (Route::Login, Self::Login(_))
            | (Route::Mgt, Self::Mgts(_))
            | (Route::NotFound, Self::NotFound)
            | (Route::OstPools, Self::OstPools)
            | (Route::PowerControl, Self::PowerControl)
            | (Route::Servers, Self::Servers(_))
            | (Route::Targets, Self::Targets)
            | (Route::Users, Self::Users)
            | (Route::Volumes, Self::Volumes) => true,
            (Route::OstPool(route_id), Self::OstPool(ostpool::Model { id }))
            | (Route::Server(route_id), Self::Server(server::Model { id }))
            | (Route::User(route_id), Self::User(user::Model { id }))
            | (Route::Volume(route_id), Self::Volume(volume::Model { id })) => route_id == &RouteId::from(id),
            (Route::Filesystem(route_id), Self::Filesystem(x)) => route_id == &RouteId::from(x.fs.id),
            (Route::Target(route_id), Self::Target(x)) => route_id == &RouteId::from(x.target.id),
            (Route::FsDashboard(route_id), Self::FsDashboard(fs_dashboard::Model { fs_name, .. })) => {
                &route_id.to_string() == fs_name
            }
            (Route::ServerDashboard(route_id), Self::ServerDashboard(server_dashboard::Model { host_name })) => {
                &route_id.to_string() == host_name
            }
            (Route::TargetDashboard(route_id), Self::TargetDashboard(target_dashboard::Model { target_name })) => {
                &route_id.to_string() == target_name
            }
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

        if let Self::Mgts(_) = self {
            mgts::init(cache, &mut orders.proxy(Msg::MgtsPage))
        }

        if let Self::FsDashboard(_) = self {
            fs_dashboard::init(&mut orders.proxy(Msg::FsDashboardPage))
        }

        if let Self::Dashboard(_) = self {
            dashboard::init(&mut orders.proxy(Msg::DashboardPage))
        }
    }
}
