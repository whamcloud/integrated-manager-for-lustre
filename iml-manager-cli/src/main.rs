// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod api_utils;
mod display_utils;
mod manager_cli_error;
mod stratagem;

use display_utils::{generate_table, start_spinner};
use iml_manager_cli::api_utils::{get, run_cmd};
use iml_wire_types::{ApiList, EndpointName, Host};
use std::process::exit;
use stratagem::stratagem_cli;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers
    #[structopt(name = "list")]
    List,
}

#[derive(StructOpt, Debug)]
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
        command: ServerCommand,
    },
}

fn main() {
    env_logger::builder().format_timestamp(None).init();

    dotenv::from_path("/var/lib/chroma/iml-settings.conf").expect("Could not load cli env");

    let matches = App::from_args();

    log::debug!("Matching args {:?}", matches);

    match matches {
        App::Stratagem { command } => stratagem_cli(command),
        App::Server { command } => match command {
            ServerCommand::List => {
                let stop_spinner = start_spinner("Running command...");

                let fut = get(Host::endpoint_name(), serde_json::json!({"limit": 0}));

                let result: Result<ApiList<Host>, _> = run_cmd(fut);

                stop_spinner(None);

                match result {
                    Ok(hosts) => {
                        log::debug!("Hosts: {:?}", hosts);

                        let table = generate_table(
                            &["Id", "FQDN", "State", "Nids"],
                            hosts.objects.into_iter().map(|h| {
                                vec![
                                    h.id.to_string(),
                                    h.fqdn,
                                    h.state,
                                    h.nids.unwrap_or_else(|| vec![]).join(" "),
                                ]
                            }),
                        );

                        table.printstd();

                        exit(exitcode::OK)
                    }
                    Err(e) => {
                        eprintln!("{}", e);

                        exit(exitcode::SOFTWARE);
                    }
                }
            }
        },
    }
}
