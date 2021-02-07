// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{config_utils::psql, display_utils::display_success, error::EmfManagerCliError};
use emf_cmd::CheckedCommandExt;
use emf_fs::{dir_exists, mkdirp};
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

        /// Override directory for Postgres data
        #[structopt(short, long, env = "EMF_PG_DATA_DIR")]
        data_dir: Option<String>,
    },

    /// Start requisite services
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Start,

    /// Setup running postgres
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup {
        /// Database name
        #[structopt(short, long, default_value = "emf", env = "PG_NAME")]
        db: String,

        /// Database user name
        #[structopt(short, long, default_value = "emf", env = "PG_USER")]
        user: String,
    },
}

fn check_space(path: &str) -> Result<(), EmfManagerCliError> {
    let statvfs = statvfs(path)?;

    let free = statvfs.blocks_free() as u64 * statvfs.fragment_size() / (1024 * 1024 * 1024);

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
            println!("Configuring postgres...");

            let use_custom_datadir = data_dir.is_some();
            let dir = data_dir.unwrap_or_else(|| "/var/lib/pgsql/13/data".to_string());

            if dir.contains(' ') {
                return Err(EmfManagerCliError::ConfigError(format!(
                    "Postgres data dir `{}' erroneously contains space",
                    dir
                )));
            }

            // check space
            if !skip_check {
                check_space(&dir)?;
            }

            // (un)configure Postgres13 to use data dir
            if use_custom_datadir {
                if !dir_exists(&dir).await {
                    mkdirp("/etc/systemd/system/postgresql-13.service.d/").await?;

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
            } else {
                // Ignore result
                let _ =
                    fs::remove_file("/etc/systemd/system/postgresql-13.service.d/emf.conf").await;
            };

            // initdb
            // /usr/pgsql-13/bin/postgresql-13-setup initdb
            emf_cmd::Command::new("/usr/bin/postgresql-13-setup")
                .arg("initdb")
                .checked_status()
                .await?;

            // setup pg_hba.conf
            fs::write(
                format!("{}/pg_hba.conf", dir),
                r#"local all all trust
local all all ident
host all all 127.0.0.1/32 trust
host all all ::1/128 trust
"#,
            )
            .await?;

            display_success(format!("Successfully configured postgres"));
        }
        Command::Start => restart_unit("postgresql-13.service".to_string()).await?,
        Command::Setup { db, user } => {
            println!("Setting up postgres...");

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

            display_success(format!("Successfully setup postgres"));
        }
    }
    Ok(())
}
