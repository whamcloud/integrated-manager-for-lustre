// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_manager_cli::{
    consul,
    display_utils::display_error,
    grafana, influx,
    nginx::{self, nginx_cli},
    postgres, selfname,
};
use std::process::exit;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum App {
    /// Configure Consul
    Consul {
        #[structopt(subcommand)]
        command: consul::Command,
    },
    /// Grafana setup
    Grafana {
        #[structopt(subcommand)]
        command: grafana::Command,
    },
    /// Influx config file generator
    Influx {
        #[structopt(subcommand)]
        command: influx::Command,
    },
    /// Nginx config file generator
    Nginx {
        #[structopt(subcommand)]
        command: nginx::NginxCommand,
    },
    /// PostgreSQL config file generator
    Postgres {
        #[structopt(subcommand)]
        command: postgres::Command,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let _ = dotenv::from_path("/etc/emf/bootstrap.conf");

    let name = selfname(Some("config")).unwrap_or_else(|| "emf-config".to_string());

    let matches = App::from_clap(&App::clap().bin_name(&name).name(&name).get_matches());

    tracing::debug!("Matching args {:?}", matches);

    let r = match matches {
        App::Consul { command } => consul::cli(command).await,
        App::Grafana { command } => grafana::cli(command).await,
        App::Influx { command } => influx::cli(command).await,
        App::Nginx { command } => nginx_cli(command).await,
        App::Postgres { command } => postgres::cli(command).await,
    };

    if let Err(e) = r {
        display_error(e);
        exit(1);
    }

    Ok(())
}
