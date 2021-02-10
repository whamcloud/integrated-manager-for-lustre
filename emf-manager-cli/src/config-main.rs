// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_manager_cli::{
    config_utils::EnvExt, display_utils::display_error, grafana, influx, kuma, nginx, postgres,
    selfname,
};
use std::process::exit;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum App {
    /// Bootstrap local node to be able to run EMF management services
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Bootstrap,

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
    /// Kuma config file generator
    Kuma {
        #[structopt(subcommand)]
        command: kuma::Command,
    },
    /// Nginx config file generator
    Nginx {
        #[structopt(subcommand)]
        command: nginx::Command,
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
        App::Bootstrap => {
            postgres::cli(postgres::Command::GenerateConfig(
                postgres::GenerateConfig::from_env(),
            ))
            .await?;
            postgres::cli(postgres::Command::Start).await?;
            postgres::cli(postgres::Command::Setup(postgres::Setup::from_env())).await?;

            nginx::cli(nginx::Command::GenerateSelfSignedCerts(
                nginx::GenerateSelfSignedCerts::from_env(),
            ))
            .await?;

            kuma::cli(kuma::Command::CreateDb(kuma::CreateDb::from_env())).await?;
            grafana::cli(grafana::Command::Setup(grafana::Setup::from_env())).await?;

            influx::cli(influx::Command::Start).await?;

            influx::cli(influx::Command::Setup(influx::Setup::from_env())).await?;

            kuma::cli(kuma::Command::Start).await?;

            kuma::cli(kuma::Command::Setup(kuma::Setup::from_env())).await?;

            Ok(())
        }
        App::Grafana { command } => grafana::cli(command).await,
        App::Influx { command } => influx::cli(command).await,
        App::Kuma { command } => kuma::cli(command).await,
        App::Nginx { command } => nginx::cli(command).await,
        App::Postgres { command } => postgres::cli(command).await,
    };

    if let Err(e) = r {
        display_error(e);
        exit(1);
    }

    Ok(())
}
