// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cli::{
    display_utils::display_error,
    nginx::{self, nginx_cli},
    selfname,
};
use std::process::exit;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum App {
    #[structopt(name = "nginx")]
    /// Nginx config file generator
    Nginx {
        #[structopt(subcommand)]
        command: nginx::NginxCommand,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let name = selfname(Some("config")).unwrap_or_else(|| "iml-config".to_string());

    let matches = App::from_clap(&App::clap().bin_name(&name).name(&name).get_matches());

    tracing::debug!("Matching args {:?}", matches);

    let r = match matches {
        App::Nginx { command } => nginx_cli(command).await,
    };

    if let Err(e) = r {
        display_error(e);
        exit(1);
    }

    Ok(())
}
