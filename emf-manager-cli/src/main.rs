// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_manager_cli::{
    api::{self, api_cli, graphql_cli},
    command,
    display_utils::display_error,
    error::EmfManagerCliError,
    filesystem::{self, filesystem_cli},
    run, selfname,
    server::{self, server_cli},
    snapshot::{self, snapshot_cli},
    stratagem::{self, stratagem_cli},
    target::{self, target_cli},
};
use std::{path::PathBuf, process::exit};
use structopt::clap::Shell;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum App {
    #[structopt(name = "command")]
    /// Work with commands
    Command { id: i32 },
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
    #[structopt(name = "run")]

    /// Run an input document on the EMF state-machine
    Run {
        /// Path of input document
        path: PathBuf,
    },
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
        #[structopt(short = "e", long = "executable", default_value = "emf")]
        exe: String,
        #[structopt(short = "o", long = "output")]
        output: Option<String>,
    },
}

static SETTINGS_FILE: &str = "/etc/emf/cli.conf";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let name = selfname(None).unwrap_or_else(|| "emf".to_string());

    let matches = App::from_clap(&App::clap().bin_name(&name).name(&name).get_matches());

    tracing::debug!("Matching args {:?}", matches);

    let r = match matches {
        App::Shell { .. } => Ok(()),
        _ => dotenv::from_path(SETTINGS_FILE).map_err(|_| {
            EmfManagerCliError::ConfigError(format!(
                "Could not load settings from {}, ensure EMF has been properly configured",
                SETTINGS_FILE
            ))
        }),
    };

    if let Err(e) = r {
        display_error(e);
        exit(1);
    }

    let r = match matches {
        App::Command { id } => command::cli(id).await,
        App::DebugApi(command) => api_cli(command).await,
        App::DebugQl(command) => graphql_cli(command).await,
        App::Filesystem { command } => filesystem_cli(command).await,
        App::Server { command } => server_cli(command).await,
        App::Snapshot { command } => snapshot_cli(command).await,
        App::Stratagem { command } => stratagem_cli(command).await,
        App::Target { command } => target_cli(command).await,
        App::Run { path } => run::cli(path).await,
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
