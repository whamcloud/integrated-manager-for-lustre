use seed::prelude::*;
use std::{borrow::Cow, ops::Deref};

#[derive(Clone, Eq, PartialEq, Debug)]
pub struct RouteId<'a>(Cow<'a, str>);

impl<'a> From<u32> for RouteId<'a> {
    fn from(n: u32) -> Self {
        RouteId(Cow::from(n.to_string()))
    }
}

impl<'a> From<&u32> for RouteId<'a> {
    fn from(n: &u32) -> Self {
        RouteId(Cow::from(n.to_string()))
    }
}
impl<'a> From<&'a str> for RouteId<'a> {
    fn from(n: &'a str) -> Self {
        RouteId(Cow::from(n))
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
    Filesystems,
    Filesystem(RouteId<'a>),
    Jobstats,
    Login,
    Logs,
    Mgt,
    NotFound,
    PowerControl,
    Servers,
    Server(RouteId<'a>),
    OstPools,
    OstPool(RouteId<'a>),
    Targets,
    Target(RouteId<'a>),
    Users,
    User(RouteId<'a>),
    Volumes,
    Volume(RouteId<'a>),
}

impl<'a> Route<'a> {
    pub fn path(&self) -> Vec<&str> {
        match self {
            Self::About => vec!["about"],
            Self::Activity => vec!["activity"],
            Self::Dashboard => vec!["dashboard"],
            Self::Filesystems => vec!["filesystems"],
            Self::Filesystem(id) => vec!["filesystems", id],
            Self::Jobstats => vec!["jobstats"],
            Self::Login => vec!["login"],
            Self::Logs => vec!["logs"],
            Self::Mgt => vec!["mgt"],
            Self::NotFound => vec!["404"],
            Self::OstPools => vec!["ost_pools"],
            Self::OstPool(id) => vec!["ost_pools", id],
            Self::PowerControl => vec!["power_control"],
            Self::Servers => vec!["servers"],
            Self::Server(id) => vec!["servers", id],
            Self::Targets => vec!["targets"],
            Self::Target(id) => vec!["targets", id],
            Self::Users => vec!["users"],
            Self::User(id) => vec!["users", id],
            Self::Volumes => vec!["volumes"],
            Self::Volume(id) => vec!["volumes", id],
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
            Self::Filesystems => "Filesystems".into(),
            Self::Filesystem(_) => "Filesystem Detail".into(),
            Self::Jobstats => "Jobstats".into(),
            Self::Login => "Login".into(),
            Self::Logs => "Logs".into(),
            Self::Mgt => "MGTs".into(),
            Self::NotFound => "404".into(),
            Self::OstPools => "OST Pool".into(),
            Self::OstPool(_) => "OST Pool Detail".into(),
            Self::PowerControl => "Power Control".into(),
            Self::Servers => "Servers".into(),
            Self::Server(_) => "Server Detail".into(),
            Self::Targets => "Target".into(),
            Self::Target(_) => "Target Detail".into(),
            Self::Users => "Users".into(),
            Self::User(_) => "User".into(),
            Self::Volumes => "Volumes".into(),
            Self::Volume(_) => "Volume Detail".into(),
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
            Some("filesystems") => match path.next() {
                None => Self::Filesystems,
                Some(id) => Self::Filesystem(RouteId::from(id)),
            },
            None | Some("") => Self::Dashboard,
            Some("jobstats") => Self::Jobstats,
            Some("login") => Self::Login,
            Some("logs") => Self::Logs,
            Some("mgt") => Self::Mgt,
            Some("ost_pools") => match path.next() {
                None => Self::OstPools,
                Some(id) => Self::OstPool(RouteId::from(id)),
            },
            Some("power_control") => Self::PowerControl,
            Some("servers") => match path.next() {
                None => Self::Servers,
                Some(id) => Self::Server(RouteId::from(id)),
            },
            Some("targets") => match path.next() {
                None => Self::Targets,
                Some(id) => Self::Target(RouteId::from(id)),
            },
            Some("users") => match path.next() {
                None => Self::Users,
                Some(id) => Self::User(RouteId::from(id)),
            },
            Some("volumes") => match path.next() {
                None => Self::Volumes,
                Some(id) => Self::Volume(RouteId::from(id)),
            },
            _ => Self::NotFound,
        }
    }
}
