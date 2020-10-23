// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::get_all,
    display_utils::{display_success, wrap_fut, DisplayType, IntoDisplayType as _},
    error::ImlManagerCliError,
};
use console::Term;
use iml_postgres::{get_db_pool, sqlx};
use iml_wire_types::{ApiList, ServerProfile};
use std::{
    collections::HashSet,
    io::{Error, ErrorKind},
};
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

async fn list_profiles(display_type: DisplayType) -> Result<(), ImlManagerCliError> {
    let profiles: ApiList<ServerProfile> = wrap_fut("Fetching profiles...", get_all()).await?;

    tracing::debug!("profiles: {:?}", profiles);

    let term = Term::stdout();

    tracing::debug!("Profiles: {:?}", profiles);

    let x = profiles.objects.into_display_type(display_type);

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

pub async fn cmd(cmd: Option<Cmd>) -> Result<(), ImlManagerCliError> {
    match cmd {
        None => {
            list_profiles(DisplayType::Tabular).await?;
        }
        Some(Cmd::List { display_type }) => {
            list_profiles(display_type).await?;
        }
        Some(Cmd::Load) => {
            let pool = get_db_pool(1).await?;

            let mut buf: Vec<u8> = Vec::new();
            stdin().read_to_end(&mut buf).await?;
            let profile: UserProfile = serde_json::from_slice(&buf)?;

            let repolist: Vec<String> = profile.repolist.into_iter().collect();
            let repolist_len = repolist.len();

            let count = sqlx::query!(
                "SELECT repo_name from chroma_core_repo where repo_name = ANY($1)",
                &repolist.clone()
            )
            .fetch_all(&pool)
            .await?
            .len();

            if count != repolist_len {
                return Err(Error::new(
                    ErrorKind::NotFound,
                    format!("Repos not found for profile {}", profile.name),
                )
                .into());
            }

            sqlx::query!(
                r#"
                INSERT INTO chroma_core_serverprofile
                (
                    name,
                    ui_name,
                    ui_description,
                    managed,
                    worker,
                    user_selectable,
                    initial_state,
                    ntp,
                    corosync,
                    corosync2,
                    pacemaker,
                    "default"
                )
                VALUES
                ($1, $2, $3, $4, $5, 'true', $6, $7, $8, $9, $10, 'false')
                ON CONFLICT (name)
                DO UPDATE
                SET
                ui_name = excluded.ui_name,
                ui_description = excluded.ui_description,
                managed = excluded.managed,
                worker = excluded.worker,
                user_selectable = excluded.user_selectable,
                initial_state = excluded.initial_state,
                ntp = excluded.ntp,
                corosync = excluded.corosync,
                corosync2 = excluded.corosync2,
                pacemaker = excluded.pacemaker,
                "default" = excluded.default
            "#,
                &profile.name,
                &profile.ui_name,
                &profile.ui_description,
                &profile.managed,
                &profile.worker,
                &profile.initial_state,
                &profile.ntp,
                &profile.corosync,
                &profile.corosync2,
                &profile.pacemaker
            )
            .execute(&pool)
            .await?;

            sqlx::query!(
                r#"
                INSERT INTO chroma_core_serverprofile_repolist (serverprofile_id, repo_id)
                SELECT $1, repo_id
                FROM UNNEST($2::text[])
                AS t(repo_id)
                ON CONFLICT DO NOTHING
            "#,
                &profile.name,
                &repolist
            )
            .execute(&pool)
            .await?;

            sqlx::query!(
                r#"
                INSERT INTO chroma_core_serverprofilepackage (package_name, server_profile_id)
                SELECT package_name, $2
                FROM UNNEST($1::text[])
                as t(package_name)
                ON CONFLICT DO NOTHING
                "#,
                &profile.packages.into_iter().collect::<Vec<_>>(),
                &profile.name
            )
            .execute(&pool)
            .await?;

            display_success("Profile loaded");
        }
        Some(Cmd::Remove { name }) => {
            let pool = get_db_pool(1).await?;

            sqlx::query!(
                "DELETE FROM chroma_core_serverprofile_repolist WHERE serverprofile_id = $1",
                &name
            )
            .execute(&pool)
            .await?;

            sqlx::query!(
                "DELETE FROM chroma_core_serverprofilepackage WHERE server_profile_id = $1",
                &name
            )
            .execute(&pool)
            .await?;

            sqlx::query!(
                "DELETE FROM chroma_core_serverprofile where name = $1",
                &name
            )
            .execute(&pool)
            .await?;

            display_success("Profile removed");
        }
    };

    Ok(())
}
