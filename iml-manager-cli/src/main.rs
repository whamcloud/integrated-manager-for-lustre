// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_cli::{
    api::{self, api_cli, graphql_cli},
    display_utils::display_error,
    filesystem::{self, filesystem_cli},
    selfname,
    server::{self, server_cli},
    snapshot::{self, snapshot_cli},
    stratagem::{self, stratagem_cli},
    target::{self, target_cli},
    update_repo_file::{self, update_repo_file_cli},
};

use std::process::exit;
use structopt::clap::Shell;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
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
        command: Option<server::ServerCommand>,
    },
    #[structopt(name = "filesystem")]
    /// Filesystem command
    Filesystem {
        #[structopt(subcommand)]
        command: filesystem::FilesystemCommand,
    },
    #[structopt(name = "snapshot")]
    /// Snapshot operations
    Snapshot {
        #[structopt(subcommand)]
        command: snapshot::SnapshotCommand,
    },
    #[structopt(name = "target")]
    /// Work with Targets
    Target {
        #[structopt(subcommand)]
        command: target::TargetCommand,
    },
    #[structopt(name = "update-repo")]
    /// Update Agent repo files
    UpdateRepoFile(update_repo_file::UpdateRepoFileHosts),

    #[structopt(name = "debugapi", setting = structopt::clap::AppSettings::Hidden)]
    /// Direct API Access (for testing and debug)
    DebugApi(api::ApiCommand),

    #[structopt(name = "debugql", setting = structopt::clap::AppSettings::Hidden)]
    /// Direct GraphQL Access (for testing and debug)
    DebugQl(api::GraphQlCommand),

    #[structopt(name = "shell-completion", setting = structopt::clap::AppSettings::Hidden)]
    /// Generate shell completion script
    Shell {
        shell: Shell,
        #[structopt(short = "e", long = "executable", default_value = "iml")]
        exe: String,
        #[structopt(short = "o", long = "output")]
        output: Option<String>,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let name = selfname(None).unwrap_or_else(|| "iml".to_string());

    let matches = App::from_clap(&App::clap().bin_name(&name).name(&name).get_matches());

    tracing::debug!("Matching args {:?}", matches);

    match matches {
        App::Shell { .. } => (),
        _ => dotenv::from_path("/etc/emf/emf-settings.conf")
            .or_else(|_| dotenv::from_path("/etc/iml/iml-settings.conf"))
            .or_else(|_| dotenv::from_path("/var/lib/chroma/iml-settings.conf"))
            .expect("Could not load cli env"),
    }

    let r = match matches {
        App::DebugApi(command) => api_cli(command).await,
        App::DebugQl(command) => graphql_cli(command).await,
        App::Filesystem { command } => filesystem_cli(command).await,
        App::Server { command } => server_cli(command).await,
        App::Snapshot { command } => snapshot_cli(command).await,
        App::Stratagem { command } => stratagem_cli(command).await,
        App::Target { command } => target_cli(command).await,
        App::UpdateRepoFile(config) => update_repo_file_cli(config).await,
        App::Shell { shell, exe, output } => {
            if let Some(out) = output {
                let mut o = std::fs::File::create(out)?;
                App::clap().gen_completions_to(exe, shell, &mut o);
            } else {
                App::clap().gen_completions_to(exe, shell, &mut std::io::stdout());
            };
            Ok(())
        }
    };

    if let Err(e) = r {
        display_error(e);
        exit(1);
    }

    Ok(())
}
