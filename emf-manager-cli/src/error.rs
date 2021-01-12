// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::Command;
use thiserror::Error;

#[derive(Debug)]
pub enum DurationParseError {
    NoUnit,
    InvalidUnit,
    InvalidValue,
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone)]
#[serde(rename_all = "snake_case")]
pub enum RunStratagemCommandResult {
    DurationOrderError,
    FilesystemRequired,
    FilesystemDoesNotExist,
    FilesystemUnavailable,
    InvalidArgument,
    PurgeDurationTooBig,
    ReportDurationTooBig,
    PurgeDurationTooSmall,
    ReportDurationTooSmall,
    Mdt0NotFound,
    Mdt0NotMounted,
    StratagemServerProfileNotInstalled,
    StratagemClientProfileNotInstalled,
    RequiredFieldsMissing,
    ServerError,
    UnknownError,
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct RunStratagemValidationError {
    pub code: RunStratagemCommandResult,
    pub message: String,
}

impl std::fmt::Display for DurationParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            DurationParseError::NoUnit => write!(f, "No unit specified."),
            DurationParseError::InvalidUnit => {
                write!(f, "Invalid unit. Valid units include 'h' and 'd'.")
            }
            DurationParseError::InvalidValue => {
                write!(f, "Invalid value specified. Must be a valid integer.")
            }
        }
    }
}

impl std::error::Error for DurationParseError {}

#[derive(Debug, Error)]
pub enum EmfManagerCliError {
    ApiError(String),
    ClientRequestError(#[from] emf_manager_client::EmfManagerClientError),
    CmdUtilError(#[from] emf_command_utils::CmdUtilError),
    CombineEasyError(combine::stream::easy::Errors<char, &'static str, usize>),
    DoesNotExist(&'static str),
    FailedCommandError(Vec<Command>),
    FromUtf8Error(#[from] std::string::FromUtf8Error),
    Infallible(#[from] std::convert::Infallible),
    EmfGraphqlQueriesErrors(#[from] emf_graphql_queries::Errors),
    IntParseError(#[from] std::num::ParseIntError),
    IoError(#[from] std::io::Error),
    ParseDurationError(#[from] DurationParseError),
    ReqwestError(#[from] reqwest::Error),
    RunStratagemValidationError(#[from] RunStratagemValidationError),
    SerdeJsonError(#[from] serde_json::error::Error),
    TokioJoinError(#[from] tokio::task::JoinError),
    TokioTimerError(#[from] tokio::time::Error),
}

impl std::fmt::Display for EmfManagerCliError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            EmfManagerCliError::ApiError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::ClientRequestError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::CmdUtilError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::CombineEasyError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::DoesNotExist(ref err) => write!(f, "{} does not exist", err),
            EmfManagerCliError::FailedCommandError(ref xs) => {
                let failed_msg = xs.iter().fold(
                    String::from("The following commands have failed:\n"),
                    |acc, x| format!("{}{}\n", acc, x.message),
                );

                write!(f, "{}", failed_msg)
            }
            EmfManagerCliError::FromUtf8Error(ref err) => write!(f, "{}", err),
            EmfManagerCliError::EmfGraphqlQueriesErrors(ref err) => write!(f, "{}", err),
            EmfManagerCliError::Infallible(_) => {
                write!(f, "A (supposedly) impossible situation has occurred")
            }
            EmfManagerCliError::IntParseError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::IoError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::ParseDurationError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::ReqwestError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::RunStratagemValidationError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::SerdeJsonError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::TokioJoinError(ref err) => write!(f, "{}", err),
            EmfManagerCliError::TokioTimerError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::fmt::Display for RunStratagemValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for RunStratagemValidationError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

impl From<combine::stream::easy::Errors<char, &str, usize>> for EmfManagerCliError {
    fn from(err: combine::stream::easy::Errors<char, &str, usize>) -> Self {
        EmfManagerCliError::CombineEasyError(err.map_range(|_| ""))
    }
}

impl From<Vec<Command>> for EmfManagerCliError {
    fn from(xs: Vec<Command>) -> Self {
        EmfManagerCliError::FailedCommandError(xs)
    }
}
