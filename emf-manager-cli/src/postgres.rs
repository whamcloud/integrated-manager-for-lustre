// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{config_utils::psql, error::EmfManagerCliError};
use emf_cmd::CheckedCommandExt;
use emf_fs::dir_exists;
use emf_systemd::restart_unit;
use nix::sys::statvfs::statvfs;
use std::collections::HashSet;
use structopt::StructOpt;
use tokio::fs;

const CHECK_SIZE_GB: u64 = 80;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    /// Generate Postgres configs and configure data directory
    #[structopt(name = "generate-config", setting = structopt::clap::AppSettings::ColoredHelp)]
    GenerateConfig {
        /// Skip space check
        #[structopt(short, long, env = "EMF_PG_SKIP_CHECK")]
        skip_check: bool,

        /// (optional) Directory for Postgres data
        #[structopt(short, long, env = "EMF_PG_DATA_DIR")]
        data_dir: Option<String>,
    },

    /// Start requisite services
    Start,

    /// Setup running postgres
    #[structopt(name = "setup", setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup {
        /// Database name
        #[structopt(default_value = "emf", env = "EMF_PG_DB")]
        db: String,

        /// Database user name
        #[structopt(default_value = "emf", env = "EMF_PG_USER")]
        user: String,
    },
}

fn check_space(path: &str) -> Result<(), EmfManagerCliError> {
    let statvfs = statvfs(path)?;

    let free = statvfs.blocks_free() * statvfs.fragment_size() / (1024 * 1024 * 1024);

    if free >= CHECK_SIZE_GB {
        Ok(())
    } else {
        Err(EmfManagerCliError::ConfigError(format!(
            "Insufficient space for postgres database in path {:?}. {}GiB available, {}GiB required",
            path,
            free,
            CHECK_SIZE_GB,
        )))
    }
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::GenerateConfig {
            skip_check,
            data_dir,
        } => {
            // (un)configure Postgres13 to use data dir
            let dir = if let Some(dir) = data_dir {
                if dir.contains(' ') {
                    return Err(EmfManagerCliError::ConfigError(format!(
                        "Postgres data dir `{}' erroneously contains space",
                        dir
                    )));
                }
                if !dir_exists(&dir).await {
                    fs::DirBuilder::new()
                        .recursive(true)
                        .create("/etc/systemd/system/postgresql-13.service.d/")
                        .await?;
                    fs::write(
                        "/etc/systemd/system/postgresql-13.service.d/emf.conf",
                        format!(
                            r#"[Service]
Environment=PGDATA={}"#,
                            dir
                        ),
                    )
                    .await?;
                }
                dir
            } else {
                // Ignore result
                let _ =
                    fs::remove_file("/etc/systemd/system/postgresql-13.service.d/emf.conf").await;
                "/var/lib/pgsql/13/data".to_string()
            };

            // initdb
            // /usr/pgsql-13/bin/postgresql-13-setup initdb
            emf_cmd::Command::new("/usr/bin/postgresql-13-setup")
                .arg("initdb")
                .checked_status()
                .await?;

            // check space
            if !skip_check {
                check_space(&dir)?;
            }

            // setup pg_hba.conf
            // /var/lib/pgsql/13/data/pg_hba.conf
            fs::write(
                format!("{}/pg_hba.conf", dir),
                r#"local all all trust
local all all ident
host all all 127.0.0.1/32 trust
host all all ::1/128 trust
"#,
            )
            .await?;
        }
        Command::Start => restart_unit("postgresql-13.service".to_string()).await?,
        Command::Setup { db, user } => {
            let users: HashSet<String> = psql("SELECT rolname FROM pg_roles")
                .await?
                .lines()
                .map(|x| x.to_string())
                .collect();
            if !users.contains(&user) {
                psql(&format!(
                    "CREATE USER {} NOSUPERUSER NOCREATEROLE INHERIT",
                    user
                ))
                .await?;
            }
            let dbs: HashSet<String> = psql("SELECT datname FROM pg_database")
                .await?
                .lines()
                .map(|x| x.to_string())
                .collect();
            if !dbs.contains(&db) {
                psql(&format!("CREATE DATABASE {} OWNER {}", db, user)).await?;
            }
        }
    }
    Ok(())
}
