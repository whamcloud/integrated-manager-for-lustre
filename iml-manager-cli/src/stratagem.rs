// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{delete, first, get, post, put, wait_for_cmd, CmdWrapper},
    display_utils::{display_cmd_state, generate_table, start_spinner},
    error::{
        DurationParseError, ImlManagerCliError, RunStratagemCommandResult,
        RunStratagemValidationError,
    },
};
use iml_manager_client_3::ImlManagerClientError;
use iml_wire_types::{ApiList, EndpointName, Filesystem, StratagemConfiguration};
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
async fn fetch_one<T: EndpointName + std::fmt::Debug + serde::de::DeserializeOwned>(
    params: impl serde::Serialize,
) -> Result<T, ImlManagerCliError> {
    let x = get(T::endpoint_name(), params).await?;

    first(x)
}

async fn get_stratagem_config_by_fs_name(
    name: &str,
) -> Result<StratagemConfiguration, ImlManagerCliError> {
    let fs: Filesystem = fetch_one(serde_json::json!({
        "name": name,
        "dehydrate__mgt": false
    }))
    .await?;

    fetch_one(serde_json::json!({ "filesystem": fs.id })).await
}

async fn handle_cmd_resp(
    resp: iml_manager_client_3::Response,
) -> Result<CmdWrapper, ImlManagerCliError> {
    let status = resp.status();

    let body = resp.text().await.map_err(ImlManagerClientError::from)?;

    if status.is_success() {
        Ok(serde_json::from_str::<CmdWrapper>(&body)?)
    } else if status.is_client_error() {
        tracing::debug!("body: {:?}", body);

        serde_json::from_str::<RunStratagemValidationError>(&body)
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

pub async fn stratagem_cli(command: StratagemCommand) -> Result<(), ImlManagerCliError> {
    match command {
        StratagemCommand::Scan(data) => {
            let r = post("run_stratagem", data).await?;

            let CmdWrapper { command } = handle_cmd_resp(r).await?;

            let stop_spinner = start_spinner(&command.message);

            let command = wait_for_cmd(command).await?;

            stop_spinner(None);

            display_cmd_state(&command);
        }
        StratagemCommand::StratagemInterval(x) => match x {
            StratagemInterval::List => {
                let stop_spinner = start_spinner("Finding existing intervals...");

                let r: ApiList<StratagemConfiguration> = get(
                    StratagemConfiguration::endpoint_name(),
                    serde_json::json!({ "limit": 0 }),
                )
                .await?;

                stop_spinner(None);

                if r.objects.is_empty() {
                    println!("No Stratagem intervals found");
                    return Ok(());
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
            }
            StratagemInterval::Add(c) => {
                let r = post(StratagemConfiguration::endpoint_name(), c).await?;

                let CmdWrapper { command } = handle_cmd_resp(r).await?;

                let stop_spinner = start_spinner(&command.message);

                let command = wait_for_cmd(command).await?;

                stop_spinner(None);

                display_cmd_state(&command);
            }
            StratagemInterval::Update(c) => {
                let x = get_stratagem_config_by_fs_name(&c.filesystem).await?;

                let r = put(
                    &format!("{}/{}", StratagemConfiguration::endpoint_name(), x.id),
                    c,
                )
                .await?;

                let CmdWrapper { command } = handle_cmd_resp(r).await?;

                let stop_spinner = start_spinner(&command.message);

                let command = wait_for_cmd(command).await?;

                stop_spinner(None);

                display_cmd_state(&command);
            }
            StratagemInterval::Remove(StratagemRemoveData { name }) => {
                let x = get_stratagem_config_by_fs_name(&name).await?;

                let r = delete(
                    &format!("{}/{}", StratagemConfiguration::endpoint_name(), x.id),
                    Vec::<(String, String)>::new(),
                )
                .await?;

                let CmdWrapper { command } = handle_cmd_resp(r).await?;

                let stop_spinner = start_spinner(&command.message);

                let command = wait_for_cmd(command).await?;

                stop_spinner(None);

                display_cmd_state(&command);
            }
        },
    };

    Ok(())
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
