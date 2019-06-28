// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;
use iml_manager_cli::{
    api_utils,
    manager_cli_error::{
        DurationParseError, ImlManagerCliError, RunStratagemCommandResult,
        RunStratagemValidationError,
    },
};
use iml_wire_types::{ApiList, Command, Host};
use prettytable::{Row, Table};
use spinners::{Spinner, Spinners};
use std::{fmt::Display, process::exit};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum StratagemCommand {
    /// Kickoff a Stratagem scan
    #[structopt(name = "scan")]
    Scan {
        /// The name of the filesystem to scan
        #[structopt(short = "f", long = "filesystem")]
        fs: String,
        /// The report duration
        #[structopt(short = "r", long = "report", parse(try_from_str = "parse_duration"))]
        rd: Option<u32>,
        /// The purge duration
        #[structopt(short = "p", long = "purge", parse(try_from_str = "parse_duration"))]
        pd: Option<u32>,
    },
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
struct StratagemCommandData {
    filesystem: String,
    report_duration: Option<u32>,
    purge_duration: Option<u32>,
}

fn parse_duration(src: &str) -> Result<u32, ImlManagerCliError> {
    if src.len() < 2 {
        return Err(DurationParseError::InvalidValue.into());
    }

    let mut val = String::from(src);
    let unit = val.pop();

    let val = val.parse::<u32>()?;

    match unit {
        Some('h') => Ok(val * 3_600),
        Some('d') => Ok(val * 86_400),
        Some('1'...'9') => Err(DurationParseError::NoUnit.into()),
        _ => Err(DurationParseError::InvalidUnit.into()),
    }
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
    if cmd.errored {
        display_error(format!("{} errored", cmd.message));
    } else if cmd.cancelled {
        println!("🚫 {} cancelled", cmd.message);
    } else if cmd.complete {
        display_success(format!("{} successful", cmd.message));
    }
}

fn display_success(message: impl Display) {
    let green = termion::color::Fg(termion::color::Green);
    let reset = termion::color::Fg(termion::color::Reset);

    println!("{}✔{} {}", green, reset, message);
}

fn display_error(message: impl Display) {
    let red = termion::color::Fg(termion::color::Red);
    let reset = termion::color::Fg(termion::color::Reset);

    println!("{}✗{} {}", red, reset, message);
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
            StratagemCommand::Scan { fs, rd, pd } => {
                let fut = {
                    let client =
                        iml_manager_client::get_client().expect("Could not create API client");
                    iml_manager_client::post(
                        client,
                        "run_stratagem",
                        serde_json::json!(StratagemCommandData {
                            filesystem: fs,
                            report_duration: rd,
                            purge_duration: pd
                        }),
                    )
                    .and_then(|resp| iml_manager_client::concat_body(resp))
                    .from_err()
                    .and_then(|(resp, body)| {
                        let status = resp.status();
                        if status.is_success() {
                            Ok(serde_json::from_slice::<CmdWrapper>(&body)?)
                        } else if status.is_client_error() {
                            serde_json::from_slice::<RunStratagemValidationError>(&body)
                                .map(std::convert::Into::into)
                                .map(Err)?
                        } else if status.is_server_error() {
                            Err(RunStratagemValidationError {
                                code: RunStratagemCommandResult::ServerError,
                                message: "Internal server error.".into(),
                            }
                            .into())
                        } else {
                            Err(RunStratagemValidationError {
                                code: RunStratagemCommandResult::UnknownError,
                                message: "Unknown error.".into(),
                            }
                            .into())
                        }
                    })
                };

                let command: Result<CmdWrapper, ImlManagerCliError> = run_cmd(fut);

                match command {
                    Ok(CmdWrapper { command }) => {
                        let stop_spinner = start_spinner(&command.message);

                        let command = run_cmd(api_utils::wait_for_cmd(command))
                            .expect("Could not poll command");

                        stop_spinner(None);

                        display_cmd_state(&command);

                        exit(exitcode::OK)
                    }
                    Err(validation_error) => {
                        display_error(validation_error);

                        exit(exitcode::CANTCREAT)
                    }
                }
            }
        },
        App::Server { command } => match command {
            ServerCommand::List => {
                let stop_spinner = start_spinner("Running command...");

                let fut = {
                    let client =
                        iml_manager_client::get_client().expect("Could not create API client");
                    iml_manager_client::get(client, "host")
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_duration_with_days() {
        match parse_duration("273d") {
            Ok(x) => assert_eq!(x, 23587200),
            Err(_) => panic!("Duration parser should not have errored!"),
        }
    }

    #[test]
    fn test_parse_duration_with_hours() {
        match parse_duration("273h") {
            Ok(x) => assert_eq!(x, 982800),
            Err(_) => panic!("Duration parser should not have errored!"),
        }
    }

    #[test]
    fn test_parse_duration_with_invalid_unit() {
        match parse_duration("273x") {
            Ok(_) => panic!("Duration should have Errored with InvalidUnit"),
            Err(e) => assert_eq!(
                e.to_string(),
                "Invalid unit. Valid units include 'h' and 'd'."
            ),
        }
    }

    #[test]
    fn test_parse_duration_without_unit() {
        match parse_duration("273") {
            Ok(_) => panic!("Duration should have Errored with NoUnit"),
            Err(e) => assert_eq!(e.to_string(), "No unit specified."),
        }
    }

    #[test]
    fn test_parse_duration_with_insufficient_data() {
        match parse_duration("2") {
            Ok(_) => panic!("Duration should have Errored with InvalidValue"),
            Err(e) => assert_eq!(
                e.to_string(),
                "Invalid value specified. Must be a valid integer."
            ),
        }
    }

    #[test]
    fn test_parse_duration_with_invalid_data() {
        match parse_duration("abch") {
            Ok(_) => panic!("Duration should have Errored with invalid digit"),
            Err(e) => assert_eq!(e.to_string(), "invalid digit found in string"),
        }
    }
}
