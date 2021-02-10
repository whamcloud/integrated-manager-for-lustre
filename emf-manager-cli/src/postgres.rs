// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{config_utils::psql, display_utils::display_success, error::EmfManagerCliError};
use emf_cmd::CheckedCommandExt;
use emf_systemd::restart_unit;
use nix::{errno::Errno, sys::statvfs::statvfs};
use regex::Regex;
use std::{collections::HashSet, path::PathBuf};
use structopt::StructOpt;
use tokio::fs;

const CHECK_SIZE_GB: u64 = 80;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    /// Generate Postgres configs and configure data directory
    #[structopt(name = "generate-config", setting = structopt::clap::AppSettings::ColoredHelp)]
    GenerateConfig(GenerateConfig),

    /// Start requisite services
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Start,

    /// Setup running postgres
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup(Setup),
}

#[derive(Debug, Default, StructOpt)]
pub struct GenerateConfig {
    /// Skip space check
    #[structopt(short, long, env = "EMF_PG_SKIP_CHECK")]
    skip_check: bool,
}

#[derive(Debug, Default, StructOpt)]
pub struct Setup {
    /// Database name
    #[structopt(short, long, default_value = "emf", env = "PG_NAME")]
    db: String,

    /// Database user name
    #[structopt(short, long, default_value = "emf", env = "PG_USER")]
    user: String,
}

fn check_space(path: &str) -> Result<(), EmfManagerCliError> {
    let mut dir: PathBuf = path.into();
    let statvfs = loop {
        match statvfs(&dir) {
            Ok(s) => break s,
            Err(nix::Error::Sys(Errno::ENOENT)) => {}
            Err(e) => return Err(EmfManagerCliError::NixError(e)),
        }
        if !dir.pop() {
            tracing::error!("Could not find valid directory in path: {}", path);
            return Err(EmfManagerCliError::NixError(nix::Error::Sys(Errno::ENOENT)));
        }
    };

    let free = statvfs.blocks_free() as u64 * statvfs.fragment_size() / (1024 * 1024 * 1024);

    if free >= CHECK_SIZE_GB {
        Ok(())
    } else {
        Err(EmfManagerCliError::ConfigError(format!(
            "Insufficient space for postgres database in path {}. {}GiB available, {}GiB required",
            path, free, CHECK_SIZE_GB,
        )))
    }
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::GenerateConfig(GenerateConfig { skip_check }) => {
            println!("Configuring postgres...");

            let out = emf_cmd::Command::new("/usr/bin/systemctl")
                .args(&["show", "-p", "Environment", "postgres-13.service"])
                .checked_output()
                .await?;
            let out = String::from_utf8_lossy(&out.stdout).to_string();
            let re = Regex::new(r"PGDATA=([^\s]+)")?;
            let dir = re
                .captures(&out)
                .map(|c| c.get(0).map(|m| m.as_str()))
                .flatten()
                .unwrap_or("/var/lib/pgsql/13/data");

            tracing::debug!("D: Using pg_dir: {}", dir);

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

            let hba_file = format!("{}/pg_hba.conf", dir);

            if emf_fs::file_exists(&hba_file).await {
                tracing::info!("Postgres already configured");
                return Ok(());
            }

            // initdb
            emf_cmd::Command::new("/usr/bin/postgresql-13-setup")
                .arg("initdb")
                .checked_status()
                .await?;

            // setup pg_hba.conf
            fs::write(
                hba_file,
                r#"local all all trust
local all all ident
host all all 127.0.0.1/32 trust
host all all ::1/128 trust
"#,
            )
            .await?;

            display_success("Successfully configured postgres".to_string());
        }
        Command::Start => restart_unit("postgresql-13.service".to_string()).await?,
        Command::Setup(Setup { db, user }) => {
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

            display_success("Successfully setup postgres".to_string());
        }
    }
    Ok(())
}
