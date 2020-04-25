// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::get_all,
    display_utils::{display_success, wrap_fut, DisplayType, IntoDisplayType as _},
    error::ImlManagerCliError,
};
use console::Term;
use iml_orm::{profile, repo, tokio_diesel::AsyncRunQueryDsl as _};
use iml_wire_types::{ApiList, ServerProfile};
use std::io::{Error, ErrorKind};
use structopt::StructOpt;
use tokio::io::{stdin, AsyncReadExt};

#[derive(Debug, StructOpt)]
pub enum Cmd {
    /// List all profiles
    #[structopt(name = "list")]
    List {
        /// Set the display type
        ///
        /// The display type can be one of the following:
        /// tabular: display content in a table format
        /// json: return data in json format
        /// yaml: return data in yaml format
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

async fn list_profiles(display_type: DisplayType) -> Result<(), ImlManagerCliError> {
    let profiles: ApiList<ServerProfile> = wrap_fut("Fetching profiles...", get_all()).await?;

    tracing::debug!("profiles: {:?}", profiles);

    let term = Term::stdout();

    tracing::debug!("Profiles: {:?}", profiles);

    let x = profiles.objects.into_display_type(display_type);

    term.write_line(&x).unwrap();

    Ok(())
}

pub async fn cmd(cmd: Option<Cmd>) -> Result<(), ImlManagerCliError> {
    match cmd {
        None => {
            list_profiles(DisplayType::Tabular).await?;
        }
        Some(Cmd::List { display_type }) => {
            list_profiles(display_type).await?;
        }
        Some(Cmd::Load) => {
            let pool = iml_orm::pool()?;

            let mut buf: Vec<u8> = Vec::new();
            stdin().read_to_end(&mut buf).await?;
            let s = String::from_utf8_lossy(&buf);
            let profile: profile::UserProfile = serde_json::from_str(&s)?;

            let xs: Vec<repo::ChromaCoreRepo> = repo::ChromaCoreRepo::by_names(&profile.repolist)
                .get_results_async(&pool)
                .await?;

            if xs.len() != profile.repolist.len() {
                return Err(Error::new(
                    ErrorKind::NotFound,
                    format!("Repos not found for profile {}", profile.name),
                )
                .into());
            }

            profile::upsert_user_profile(profile, &pool).await?;

            display_success("Profile loaded");
        }
        Some(Cmd::Remove { name }) => {
            let pool = iml_orm::pool()?;

            profile::remove_profile_by_name(name, &pool).await?;

            display_success("Profile removed");
        }
    };

    Ok(())
}
