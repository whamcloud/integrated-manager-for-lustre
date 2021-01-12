// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql,
    display_utils::{display_success, wrap_fut, DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use console::Term;
use emf_graphql_queries::server_profile;
use emf_wire_types::graphql::ServerProfileInput;
use std::collections::HashSet;
use structopt::StructOpt;
use tokio::io::{stdin, AsyncReadExt};

#[derive(Debug, StructOpt)]
pub enum Cmd {
    /// List all profiles
    #[structopt(name = "list")]
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Load a new profile from stdin
    #[structopt(name = "load")]
    Load,
    /// Remove an existing profile
    #[structopt(name = "remove")]
    Remove { name: String },
}

async fn list_profiles(display_type: DisplayType) -> Result<(), EmfManagerCliError> {
    let query = server_profile::list::build();

    let resp: emf_graphql_queries::Response<server_profile::list::Resp> =
        wrap_fut("Fetching profiles", graphql(query)).await?;
    let server_profiles = Result::from(resp)?.data.server_profiles;

    tracing::debug!("profiles: {:?}", server_profiles);

    let x = server_profiles.into_display_type(display_type);

    let term = Term::stdout();

    term.write_line(&x).unwrap();

    Ok(())
}

#[derive(serde::Deserialize)]
pub struct UserProfile {
    pub corosync: bool,
    pub corosync2: bool,
    pub initial_state: String,
    pub managed: bool,
    pub name: String,
    pub ntp: bool,
    pub pacemaker: bool,
    pub packages: HashSet<String>,
    pub repolist: HashSet<String>,
    pub ui_description: String,
    pub ui_name: String,
    pub worker: bool,
}

impl Into<ServerProfileInput> for UserProfile {
    fn into(self) -> ServerProfileInput {
        ServerProfileInput {
            corosync: self.corosync,
            corosync2: self.corosync2,
            default: false,
            initial_state: self.initial_state,
            managed: self.managed,
            name: self.name,
            ntp: self.ntp,
            pacemaker: self.pacemaker,
            packages: self.packages.into_iter().collect(),
            repolist: self.repolist.into_iter().collect(),
            ui_description: self.ui_description,
            ui_name: self.ui_name,
            user_selectable: true,
            worker: self.worker,
        }
    }
}

pub async fn cmd(cmd: Option<Cmd>) -> Result<(), EmfManagerCliError> {
    match cmd {
        None => {
            list_profiles(DisplayType::Tabular).await?;
        }
        Some(Cmd::List { display_type }) => {
            list_profiles(display_type).await?;
        }
        Some(Cmd::Load) => {
            let mut buf: Vec<u8> = Vec::new();
            stdin().read_to_end(&mut buf).await?;
            let profile: UserProfile = serde_json::from_slice(&buf)?;
            let input: ServerProfileInput = profile.into();

            let query = server_profile::create::build(input);

            let resp: emf_graphql_queries::Response<server_profile::create::Resp> =
                wrap_fut("Loading profile", graphql(query)).await?;
            let _success = Result::from(resp)?.data.create_server_profile;

            display_success("Profile loaded");
        }
        Some(Cmd::Remove { name }) => {
            let query = server_profile::remove::build(&name);

            let resp: emf_graphql_queries::Response<server_profile::remove::Resp> =
                wrap_fut("Removing profile", graphql(query)).await?;
            let _success = Result::from(resp)?.data.remove_server_profile;

            display_success("Profile removed");
        }
    };

    Ok(())
}
