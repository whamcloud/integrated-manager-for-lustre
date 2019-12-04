use seed::prelude::*;
use std::{borrow::Cow, ops::Deref};

#[derive(Clone, Eq, PartialEq)]
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

#[derive(Clone, Eq, PartialEq)]
pub enum Route<'a> {
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
    ServerDetail(RouteId<'a>),
    Target,
    User,
    Volume,
}

impl<'a> Route<'a> {
    pub fn path(&self) -> Vec<&str> {
        match self {
            Self::About => vec!["about"],
            Self::Activity => vec!["activity"],
            Self::Dashboard => vec!["dashboard"],
            Self::Filesystem => vec!["filesystem"],
            Self::FilesystemDetail => vec!["filesystem_detail"],
            Self::Home => vec![""],
            Self::Jobstats => vec!["jobstats"],
            Self::Login => vec!["login"],
            Self::Logs => vec!["logs"],
            Self::Mgt => vec!["mgt"],
            Self::NotFound => vec!["404"],
            Self::PowerControl => vec!["power_control"],
            Self::Server => vec!["server"],
            Self::ServerDetail(id) => vec!["server_detail", &id],
            Self::Target => vec!["target"],
            Self::User => vec!["user"],
            Self::Volume => vec!["volume"],
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
            Self::FilesystemDetail => "Filesystem Detail".into(),
            Self::Home => "Home".into(),
            Self::Jobstats => "Jobstats".into(),
            Self::Login => "Login".into(),
            Self::Logs => "Logs".into(),
            Self::Mgt => "MGTs".into(),
            Self::NotFound => "404".into(),
            Self::PowerControl => "Power Control".into(),
            Self::Server => "Servers".into(),
            Self::ServerDetail(_) => "Server Detail".into(),
            Self::Target => "Target".into(),
            Self::User => "Users".into(),
            Self::Volume => "Volumes".into(),
        }
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
            Some("filesystem_detail") => Self::FilesystemDetail,
            None | Some("") => Self::Home,
            Some("jobstats") => Self::Jobstats,
            Some("login") => Self::Login,
            Some("logs") => Self::Logs,
            Some("mgt") => Self::Mgt,
            Some("power_control") => Self::PowerControl,
            Some("server") => Self::Server,
            Some("server_detail") => path
                .next()
                .map(RouteId::from)
                .map(Self::ServerDetail)
                .unwrap_or(Self::NotFound),
            Some("target") => Self::Target,
            Some("user") => Self::User,
            Some("volume") => Self::Volume,
            _ => Self::NotFound,
        }
    }
}
