// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{delete, first, get, post, put, run_cmd, wait_for_cmd, CmdWrapper},
    display_utils::{display_cmd_state, display_error, generate_table, start_spinner},
    manager_cli_error::{
        DurationParseError, ImlManagerCliError, RunStratagemCommandResult,
        RunStratagemValidationError,
    },
};
use futures::Future;
use iml_wire_types::{ApiList, EndpointName, Filesystem, StratagemConfiguration};
use std::process::exit;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum StratagemCommand {
    /// Kickoff a Stratagem scan
    #[structopt(name = "scan")]
    Scan(StratagemScanData),
    /// Configure Stratagem scanning interval
    #[structopt(name = "interval")]
    StratagemInterval(StratagemInterval),
}

#[derive(Debug, StructOpt)]
pub enum StratagemInterval {
    /// List all existing Stratagem intervals
    #[structopt(name = "list")]
    List,
    /// Add a new Stratagem interval
    #[structopt(name = "add")]
    Add(StratagemIntervalConfig),
    /// Update an existing Stratagem interval
    #[structopt(name = "update")]
    Update(StratagemIntervalConfig),
    /// Remove a Stratagem interval
    #[structopt(name = "remove")]
    Remove(StratagemRemoveData),
}

#[derive(Debug, StructOpt, serde::Serialize)]
pub struct StratagemIntervalConfig {
    /// Filesystem to configure
    #[structopt(short = "f", long = "filesystem")]
    filesystem: String,
    /// Interval to scan
    #[structopt(short = "i", long = "interval", parse(try_from_str = "parse_duration"))]
    interval: u64,
    /// The report duration
    #[structopt(short = "r", long = "report", parse(try_from_str = "parse_duration"))]
    report_duration: Option<u64>,
    /// The purge duration
    #[structopt(short = "p", long = "purge", parse(try_from_str = "parse_duration"))]
    purge_duration: Option<u64>,
}

#[derive(Debug, StructOpt, serde::Serialize)]
pub struct StratagemRemoveData {
    /// Filesystem to unconfigure
    #[structopt(short = "f", long = "filesystem")]
    name: String,
}

#[derive(serde::Serialize, StructOpt, Debug)]
pub struct StratagemScanData {
    /// The name of the filesystem to scan
    #[structopt(short = "f", long = "filesystem")]
    filesystem: String,
    /// The report duration
    #[structopt(short = "r", long = "report", parse(try_from_str = "parse_duration"))]
    report_duration: Option<u64>,
    /// The purge duration
    #[structopt(short = "p", long = "purge", parse(try_from_str = "parse_duration"))]
    purge_duration: Option<u64>,
}

fn parse_duration(src: &str) -> Result<u64, ImlManagerCliError> {
    if src.len() < 2 {
        return Err(DurationParseError::InvalidValue.into());
    }

    let mut val = String::from(src);
    let unit = val.pop();

    let val = val.parse::<u64>()?;

    match unit {
        Some('h') => Ok(val * 3_600_000),
        Some('d') => Ok(val * 86_400_000),
        Some('m') => Ok(val * 60_000),
        Some('s') => Ok(val * 1_000),
        Some('1'..='9') => Err(DurationParseError::NoUnit.into()),
        _ => Err(DurationParseError::InvalidUnit.into()),
    }
}

/// Given some params, does a fetch for the item in the API
fn fetch_one<T: EndpointName + std::fmt::Debug + serde::de::DeserializeOwned>(
    params: impl serde::Serialize,
) -> impl Future<Item = T, Error = ImlManagerCliError> {
    get(T::endpoint_name(), params).and_then(first)
}

fn get_stratagem_config_by_fs_name(
    name: &str,
) -> impl Future<Item = StratagemConfiguration, Error = ImlManagerCliError> {
    fetch_one(serde_json::json!({
        "name": name,
        "dehydrate__mgt": false
    }))
    .and_then(|fs: Filesystem| fetch_one(serde_json::json!({ "filesystem": fs.id })))
}

fn handle_cmd_resp(
    (resp, body): (iml_manager_client::Response, iml_manager_client::Chunk),
) -> Result<CmdWrapper, ImlManagerCliError> {
    let status = resp.status();
    if status.is_success() {
        Ok(serde_json::from_slice::<CmdWrapper>(&body)?)
    } else if status.is_client_error() {
        log::debug!("body: {:?}", std::str::from_utf8(&body));
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
}

pub fn stratagem_cli(command: StratagemCommand) {
    match command {
        StratagemCommand::Scan(data) => {
            let fut = post("run_stratagem", data).and_then(handle_cmd_resp);

            let command: Result<CmdWrapper, ImlManagerCliError> = run_cmd(fut);

            match command {
                Ok(CmdWrapper { command }) => {
                    let stop_spinner = start_spinner(&command.message);

                    let command = run_cmd(wait_for_cmd(command)).expect("Could not poll command");

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
        StratagemCommand::StratagemInterval(x) => match x {
            StratagemInterval::List => {
                let stop_spinner = start_spinner("Finding existing intervals...");

                let fut = get(
                    StratagemConfiguration::endpoint_name(),
                    serde_json::json!({ "limit": 0 }),
                );
                let result: Result<ApiList<StratagemConfiguration>, _> = run_cmd(fut);

                stop_spinner(None);

                match result {
                    Ok(r) => {
                        if r.objects.is_empty() {
                            return println!("No Stratagem intervals found");
                        }

                        let table = generate_table(
                            &["Id", "Filesystem", "State", "Interval", "Purge", "Report"],
                            r.objects.into_iter().map(|x| {
                                vec![
                                    x.id.to_string(),
                                    x.filesystem,
                                    x.state,
                                    x.interval.to_string(),
                                    x.purge_duration.map(|x| x.to_string()).unwrap_or_default(),
                                    x.report_duration.map(|x| x.to_string()).unwrap_or_default(),
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
            StratagemInterval::Add(c) => {
                let fut =
                    post(StratagemConfiguration::endpoint_name(), c).and_then(handle_cmd_resp);

                let command: Result<CmdWrapper, ImlManagerCliError> = run_cmd(fut);

                match command {
                    Ok(CmdWrapper { command }) => {
                        let stop_spinner = start_spinner(&command.message);

                        let command =
                            run_cmd(wait_for_cmd(command)).expect("Could not poll command");

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
            StratagemInterval::Update(c) => {
                let fut = get_stratagem_config_by_fs_name(&c.filesystem)
                    .and_then(|x| {
                        put(
                            &format!("{}/{}", StratagemConfiguration::endpoint_name(), x.id),
                            c,
                        )
                    })
                    .and_then(handle_cmd_resp);

                let command: Result<CmdWrapper, ImlManagerCliError> = run_cmd(fut);

                match command {
                    Ok(CmdWrapper { command }) => {
                        let stop_spinner = start_spinner(&command.message);

                        let command =
                            run_cmd(wait_for_cmd(command)).expect("Could not poll command");

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
            StratagemInterval::Remove(StratagemRemoveData { name }) => {
                let fut = get_stratagem_config_by_fs_name(&name)
                    .and_then(|x: StratagemConfiguration| {
                        delete(
                            &format!("{}/{}", StratagemConfiguration::endpoint_name(), x.id),
                            Vec::<(String, String)>::new(),
                        )
                    })
                    .and_then(handle_cmd_resp);

                let x: Result<CmdWrapper, ImlManagerCliError> = run_cmd(fut);

                match x {
                    Ok(CmdWrapper { command }) => {
                        let stop_spinner = start_spinner(&command.message);

                        let command =
                            run_cmd(wait_for_cmd(command)).expect("Could not poll command");

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
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_duration_with_days() {
        match parse_duration("273d") {
            Ok(x) => assert_eq!(x, 23_587_200_000),
            _ => panic!("Duration parser should not have errored!"),
        }
    }

    #[test]
    fn test_parse_duration_with_hours() {
        match parse_duration("273h") {
            Ok(x) => assert_eq!(x, 982_800_000),
            _ => panic!("Duration parser should not have errored!"),
        }
    }

    #[test]
    fn test_parse_duration_with_minutes() {
        match parse_duration("273m") {
            Ok(x) => assert_eq!(x, 16_380_000),
            _ => panic!("Duration parser should not have errored!"),
        }
    }

    #[test]
    fn test_parse_duration_with_seconds() {
        match parse_duration("273s") {
            Ok(x) => assert_eq!(x, 273_000),
            _ => panic!("Duration parser should not have errored!"),
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
