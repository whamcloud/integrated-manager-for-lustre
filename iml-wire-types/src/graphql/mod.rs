pub mod duration;
pub mod json;
pub mod map;

use crate::db::ServerProfileRecord;

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct ServerProfile {
    pub corosync: bool,
    pub corosync2: bool,
    pub default: bool,
    pub initial_state: String,
    pub managed: bool,
    pub name: String,
    pub ntp: bool,
    pub pacemaker: bool,
    pub ui_description: String,
    pub ui_name: String,
    pub user_selectable: bool,
    pub worker: bool,
    pub repos: Vec<Repository>,
}

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
pub struct ServerProfileInput {
    pub corosync: bool,
    pub corosync2: bool,
    pub default: bool,
    #[serde(rename(serialize = "initialState"))]
    pub initial_state: String,
    pub managed: bool,
    pub name: String,
    pub ntp: bool,
    pub pacemaker: bool,
    #[serde(rename(serialize = "uiDescription"))]
    pub ui_description: String,
    #[serde(rename(serialize = "uiName"))]
    pub ui_name: String,
    #[serde(rename(serialize = "userSelectable"))]
    pub user_selectable: bool,
    pub worker: bool,
    pub packages: Vec<String>,
    pub repolist: Vec<String>,
}

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct Repository {
    pub name: String,
    pub location: String,
}

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
pub struct RepositoryInput {
    pub name: String,
    pub location: String,
}

impl ServerProfile {
    pub fn new(
        record: ServerProfileRecord,
        repos: &serde_json::Value,
    ) -> Result<Self, &'static str> {
        let repos: Vec<_> = repos
            .as_array()
            .ok_or("repos is not an array")?
            .iter()
            .filter_map(|p| {
                let name = p.get("f1")?;
                let location = p.get("f2")?;
                Some(Repository {
                    name: name.as_str()?.into(),
                    location: location.as_str()?.into(),
                })
            })
            .collect();
        Ok(Self {
            corosync: record.corosync,
            corosync2: record.corosync2,
            default: record.default,
            initial_state: record.initial_state,
            managed: record.managed,
            name: record.name,
            ntp: record.ntp,
            pacemaker: record.pacemaker,
            repos,
            ui_description: record.ui_description,
            ui_name: record.ui_name,
            user_selectable: record.user_selectable,
            worker: record.worker,
        })
    }
}
