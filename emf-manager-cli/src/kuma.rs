// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{config_utils::psql, error::EmfManagerCliError};
use emf_cmd::CheckedCommandExt;
use emf_fs::mkdirp;
use emf_systemd::restart_unit;
use std::{collections::HashSet, ffi::OsStr, path::PathBuf, process::Output};
use structopt::StructOpt;
use tokio::fs;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    ///  config
    #[structopt(name = "create-db", setting = structopt::clap::AppSettings::ColoredHelp)]
    CreateDb(CreateDb),

    /// Start requisite services
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Start,

    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup(Setup),
}

#[derive(Debug, Default, StructOpt)]
pub struct CreateDb {
    /// Postgres database to use for kuma info
    #[structopt(short, long, default_value = "kuma", env = "EMF_KUMA_DB")]
    db: String,

    /// Postgres user to access database
    #[structopt(short, long, default_value = "emf", env = "EMF_KUMA_DB_USER")]
    user: String,
}

#[derive(Debug, Default, StructOpt)]
pub struct Setup {
    /// Base config dir
    #[structopt(short, long, default_value = "/etc/emf", env = "EMF_KUMA_BASE_DIR")]
    dir: PathBuf,
}

async fn kumactl<I, S>(args: I) -> Result<Output, EmfManagerCliError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let out = emf_cmd::Command::new("kumactl")
        .args(args)
        .checked_output()
        .await?;
    Ok(out)
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::CreateDb(CreateDb { db, user }) => {
            let dbs: HashSet<String> = psql("SELECT datname FROM pg_database")
                .await?
                .lines()
                .map(|x| x.to_string())
                .collect();
            if !dbs.contains(&db) {
                psql(&format!("CREATE DATABASE {} OWNER {}", db, user)).await?;
            }
        }
        Command::Start => restart_unit("kuma.service".to_string()).await?,
        Command::Setup(Setup { dir }) => {
            let tokendir = dir.join("tokens");
            let policydir = dir.join("policies");

            mkdirp(&tokendir).await?;

            let out = kumactl(vec!["generate", "dataplane-token", "--mesh", "default"]).await?;
            fs::write(tokendir.join("dataplane-token"), out.stdout).await?;

            kumactl(vec![
                "apply",
                "-f",
                policydir.join("mtls.yml").to_str().unwrap(),
            ])
            .await?;
            kumactl(vec![
                "apply",
                "-f",
                policydir.join("traffic.yml").to_str().unwrap(),
            ])
            .await?;
        }
    }
    Ok(())
}
