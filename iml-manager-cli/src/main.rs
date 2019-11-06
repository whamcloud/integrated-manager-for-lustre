// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_cli::{
    display_utils::display_error,
    filesystem::{self, filesystem_cli},
    server::{self, server_cli},
    stratagem::{self, stratagem_cli},
    update_repo_file::{self, update_repo_file_cli},
};
use std::process::exit;
use structopt::StructOpt;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[derive(Debug, StructOpt)]
#[structopt(name = "iml")]
#[structopt(raw(setting = "structopt::clap::AppSettings::ColoredHelp"))]
/// The Integrated Manager for Lustre Agent CLI
pub enum App {
    #[structopt(name = "stratagem")]
    /// Work with Stratagem server
    Stratagem {
        #[structopt(subcommand)]
        command: stratagem::StratagemCommand,
    },
    #[structopt(name = "server")]
    /// Work with Storage Servers
    Server {
        #[structopt(subcommand)]
        command: server::ServerCommand,
    },
    #[structopt(name = "filesystem")]
    /// Work with Storage Servers
    Filesystem {
        #[structopt(subcommand)]
        command: filesystem::FilesystemCommand,
    },
    #[structopt(name = "update_repo")]
    ///  Update Agent repo files
    UpdateRepoFile(update_repo_file::UpdateRepoFileHosts),
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    dotenv::from_path("/var/lib/chroma/iml-settings.conf").expect("Could not load cli env");

    let matches = App::from_args();

    tracing::debug!("Matching args {:?}", matches);

    let r = match matches {
        App::Stratagem { command } => stratagem_cli(command).await,
        App::Server { command } => server_cli(command).await,
        App::UpdateRepoFile(config) => update_repo_file_cli(config).await,
        App::Filesystem { command } => filesystem_cli(command).await,
    };

    if let Err(e) = r {
        display_error(e);
        exit(1);
    }

    Ok(())
}
