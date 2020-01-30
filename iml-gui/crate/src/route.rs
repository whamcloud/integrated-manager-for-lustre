use seed::prelude::*;
use std::{borrow::Cow, ops::Deref};

#[derive(Clone, Eq, PartialEq, Debug)]
pub struct RouteId<'a>(Cow<'a, str>);

impl<'a> From<u32> for RouteId<'a> {
    fn from(n: u32) -> Self {
        RouteId(Cow::from(n.to_string()))
    }
}

impl<'a> From<String> for RouteId<'a> {
    fn from(n: String) -> Self {
        RouteId(Cow::from(n))
    }
}

impl<'a> Deref for RouteId<'a> {
    type Target = Cow<'a, str>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

#[derive(Clone, Eq, PartialEq, Debug)]
pub enum Route<'a> {
    About,
    Activity,
    Dashboard,
    Filesystem,
    FilesystemDetail(RouteId<'a>),
    Jobstats,
    Login,
    Logs,
    Mgt,
    NotFound,
    PowerControl,
    Server,
    ServerDetail(RouteId<'a>),
    OstPool,
    OstPoolDetail(RouteId<'a>),
    Target,
    TargetDetail(RouteId<'a>),
    User,
    UserDetail(RouteId<'a>),
    Volume,
    VolumeDetail(RouteId<'a>),
}

impl<'a> Route<'a> {
    pub fn path(&self) -> Vec<&str> {
        match self {
            Self::About => vec!["about"],
            Self::Activity => vec!["activity"],
            Self::Dashboard => vec!["dashboard"],
            Self::Filesystem => vec!["filesystem"],
            Self::FilesystemDetail(id) => vec!["filesystem_detail", id],
            Self::Jobstats => vec!["jobstats"],
            Self::Login => vec!["login"],
            Self::Logs => vec!["logs"],
            Self::Mgt => vec!["mgt"],
            Self::NotFound => vec!["404"],
            Self::OstPool => vec!["ost_pool"],
            Self::OstPoolDetail(id) => vec!["ost_pool_detail", id],
            Self::PowerControl => vec!["power_control"],
            Self::Server => vec!["server"],
            Self::ServerDetail(id) => vec!["server_detail", id],
            Self::Target => vec!["target"],
            Self::TargetDetail(id) => vec!["target_detail", id],
            Self::User => vec!["user"],
            Self::UserDetail(id) => vec!["user_detail", id],
            Self::Volume => vec!["volume"],
            Self::VolumeDetail(id) => vec!["volume_detail", id],
        }
    }

    pub fn to_href(&self) -> String {
        format!("/{}", self.path().join("/"))
    }
}

impl<'a> ToString for Route<'a> {
    fn to_string(&self) -> String {
        match self {
            Self::About => "About".into(),
            Self::Activity => "Activity".into(),
            Self::Dashboard => "Dashboard".into(),
            Self::Filesystem => "Filesystems".into(),
            Self::FilesystemDetail(_) => "Filesystem Detail".into(),
            Self::Jobstats => "Jobstats".into(),
            Self::Login => "Login".into(),
            Self::Logs => "Logs".into(),
            Self::Mgt => "MGTs".into(),
            Self::NotFound => "404".into(),
            Self::OstPool => "OST Pool".into(),
            Self::OstPoolDetail(_) => "OST Pool Detail".into(),
            Self::PowerControl => "Power Control".into(),
            Self::Server => "Servers".into(),
            Self::ServerDetail(_) => "Server Detail".into(),
            Self::Target => "Target".into(),
            Self::TargetDetail(_) => "Target Detail".into(),
            Self::User => "Users".into(),
            Self::UserDetail(_) => "User".into(),
            Self::Volume => "Volumes".into(),
            Self::VolumeDetail(_) => "Volume Detail".into(),
        }
    }
}

impl<'a> From<Route<'a>> for Url {
    fn from(route: Route<'a>) -> Self {
        route.path().into()
    }
}

impl<'a> From<Url> for Route<'a> {
    fn from(url: Url) -> Self {
        let mut path = url.path.into_iter();

        match path.next().as_ref().map(String::as_str) {
            Some("about") => Self::About,
            Some("activity") => Self::Activity,
            Some("dashboard") => Self::Dashboard,
            Some("filesystem") => Self::Filesystem,
            Some("filesystem_detail") => path
                .next()
                .map(RouteId::from)
                .map(Self::FilesystemDetail)
                .unwrap_or(Self::NotFound),
            None | Some("") => Self::Dashboard,
            Some("jobstats") => Self::Jobstats,
            Some("login") => Self::Login,
            Some("logs") => Self::Logs,
            Some("mgt") => Self::Mgt,
            Some("ost_pool") => Self::OstPool,
            Some("ost_pool_detail") => path
                .next()
                .map(RouteId::from)
                .map(Self::OstPoolDetail)
                .unwrap_or(Self::NotFound),
            Some("power_control") => Self::PowerControl,
            Some("server") => Self::Server,
            Some("server_detail") => path
                .next()
                .map(RouteId::from)
                .map(Self::ServerDetail)
                .unwrap_or(Self::NotFound),
            Some("target") => Self::Target,
            Some("target_detail") => path
                .next()
                .map(RouteId::from)
                .map(Self::TargetDetail)
                .unwrap_or(Self::NotFound),
            Some("user") => Self::User,
            Some("user_detail") => path
                .next()
                .map(RouteId::from)
                .map(Self::UserDetail)
                .unwrap_or(Self::NotFound),
            Some("volume") => Self::Volume,
            Some("volume_detail") => path
                .next()
                .map(RouteId::from)
                .map(Self::VolumeDetail)
                .unwrap_or(Self::NotFound),
            _ => Self::NotFound,
        }
    }
}
