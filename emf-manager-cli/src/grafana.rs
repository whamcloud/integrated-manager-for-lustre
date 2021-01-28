// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{config_utils::psql, error::EmfManagerCliError};
use std::collections::HashSet;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    ///  config
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup {
        /// Postgres database to use for grafana info
        #[structopt(default_value = "grafana", env = "EMF_GRAFANA_DB")]
        db: String,

        /// Postgres user to access database
        #[structopt(default_value = "emf", env = "EMF_GRAFANA_DB_USER")]
        user: String,
    },
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::Setup { db, user } => {
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
