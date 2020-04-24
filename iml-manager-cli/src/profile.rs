// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::get_all,
    display_utils::{display_success, generate_table, wrap_fut},
    error::ImlManagerCliError,
};
use iml_orm::{profile, repo, tokio_diesel::AsyncRunQueryDsl as _};
use iml_wire_types::{ApiList, ServerProfile};
use std::io::{Error, ErrorKind};
use structopt::StructOpt;
use tokio::io::{stdin, AsyncReadExt};

#[derive(Debug, StructOpt)]
pub enum Cmd {
    /// List all profiles
    #[structopt(name = "list")]
    List,
    /// Load a new profile from stdin
    #[structopt(name = "load")]
    Load,
    /// Remove an existing profile
    #[structopt(name = "remove")]
    Remove { name: String },
}

pub async fn cmd(cmd: Option<Cmd>) -> Result<(), ImlManagerCliError> {
    match cmd {
        None | Some(Cmd::List) => {
            let profiles: ApiList<ServerProfile> =
                wrap_fut("Fetching profiles...", get_all()).await?;

            tracing::debug!("profiles: {:?}", profiles);

            let table = generate_table(
                &["Profile", "Name", "Description"],
                profiles
                    .objects
                    .into_iter()
                    .filter(|x| x.user_selectable)
                    .map(|x| vec![x.name, x.ui_name, x.ui_description]),
            );

            table.printstd();
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

            if &xs.len() != &profile.repolist.len() {
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
