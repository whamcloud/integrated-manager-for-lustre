// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;
use iml_manager_cli::{api_client, api_utils};
use iml_wire_types::{ApiList, Command, Host};
use prettytable::{Row, Table};
use spinners::{Spinner, Spinners};
use std::process::exit;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum StratagemCommand {
    /// Kickoff a Stratagem scan
    #[structopt(name = "scan")]
    Scan {
        /// The name of the filesystem to scan
        #[structopt(short = "fs", long = "filesystem")]
        fs: String,
    },
}

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers
    #[structopt(name = "list")]
    List,
}

#[derive(StructOpt, Debug)]
#[structopt(name = "iml")]
/// The Integrated Manager for Lustre Agent CLI
pub enum App {
    #[structopt(name = "stratagem")]
    /// Work with Stratagem server
    Stratagem {
        #[structopt(subcommand)]
        command: StratagemCommand,
    },
    #[structopt(name = "server")]
    /// Work with Storage Servers
    Server {
        #[structopt(subcommand)]
        command: ServerCommand,
    },
}

/// Takes an asynchronous computation (Future), runs it to completion
/// and returns the result.
///
/// Even though the action is asynchronous, this fn will block until
/// the future resolves.
fn run_cmd<R: Send + 'static, E: Send + 'static>(
    fut: impl Future<Item = R, Error = E> + Send + 'static,
) -> std::result::Result<R, E> {
    tokio::runtime::Runtime::new().unwrap().block_on_all(fut)
}

fn generate_table<Rows, R>(columns: &[&str], rows: Rows) -> Table
where
    R: IntoIterator,
    R::Item: ToString,
    Rows: IntoIterator<Item = R>,
{
    let mut table = Table::new();

    table.add_row(Row::from(columns));

    for r in rows {
        table.add_row(Row::from(r));
    }

    table
}

fn start_spinner(msg: &str) -> impl FnOnce(Option<String>) -> () {
    let grey = termion::color::Fg(termion::color::LightBlack);
    let reset = termion::color::Fg(termion::color::Reset);

    let s = format!("{}{}{}", grey, reset, msg);
    let s_len = s.len();

    let sp = Spinner::new(Spinners::Dots9, s);

    move |msg_opt| match msg_opt {
        Some(msg) => {
            sp.message(msg);
        }
        None => {
            sp.stop();
            print!("{}", termion::clear::CurrentLine);
            print!("{}", termion::cursor::Left(s_len as u16));
        }
    }
}

fn display_cmd_state(cmd: &Command) {
    let green = termion::color::Fg(termion::color::Green);
    let red = termion::color::Fg(termion::color::Red);
    let reset = termion::color::Fg(termion::color::Reset);

    if cmd.errored {
        println!("{}✗{} {} errored", red, reset, cmd.message);
    } else if cmd.cancelled {
        println!("🚫 {} cancelled", cmd.message);
    } else if cmd.complete {
        println!("{}✔{} {} completed", green, reset, cmd.message);
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
struct CmdWrapper {
    command: Command,
}

fn main() {
    env_logger::builder().default_format_timestamp(false).init();

    dotenv::from_path("/var/lib/chroma/iml-settings.conf").expect("Could not load cli env");

    let matches = App::from_args();

    log::debug!("Matching args {:?}", matches);

    match matches {
        App::Stratagem { command } => match command {
            StratagemCommand::Scan { fs } => {
                let fut = {
                    let client = api_client::get_client().expect("Could not create API client");
                    api_client::post(
                        client,
                        "run_stratagem",
                        serde_json::json!({ "filesystem": fs }),
                    )
                };

                let CmdWrapper { command }: CmdWrapper = run_cmd(fut).expect("Could not run cmd");

                let stop_spinner = start_spinner(&command.message);

                let command =
                    run_cmd(api_utils::wait_for_cmd(command)).expect("Could not poll command");

                stop_spinner(None);

                display_cmd_state(&command);

                exit(exitcode::OK)
            }
        },
        App::Server { command } => match command {
            ServerCommand::List => {
                let stop_spinner = start_spinner("Running command...");

                let fut = {
                    let client = api_client::get_client().expect("Could not create API client");
                    api_client::get(client, "host")
                };

                let result: Result<ApiList<Host>, _> = run_cmd(fut);

                stop_spinner(None);

                match result {
                    Ok(hosts) => {
                        log::debug!("Hosts: {:?}", hosts);

                        let table = generate_table(
                            &["Id", "FQDN", "State", "Nids"],
                            hosts
                                .objects
                                .into_iter()
                                .map(|h| vec![h.id.to_string(), h.fqdn, h.state, h.nids.join(" ")]),
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
