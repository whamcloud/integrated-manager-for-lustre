// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug)]
pub enum DurationParseError {
    NoUnit,
    InvalidUnit,
    InvalidValue,
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

#[derive(Debug)]
pub enum ImlManagerCliError {
    ClientRequestError(iml_manager_client::ImlManagerClientError),
    TokioTimerError(tokio::timer::Error),
    IntParseError(std::num::ParseIntError),
    ParseDurationError(DurationParseError),
}

impl std::fmt::Display for ImlManagerCliError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlManagerCliError::ClientRequestError(ref err) => write!(f, "{}", err),
            ImlManagerCliError::TokioTimerError(ref err) => write!(f, "{}", err),
            ImlManagerCliError::IntParseError(ref err) => write!(f, "{}", err),
            ImlManagerCliError::ParseDurationError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlManagerCliError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlManagerCliError::ClientRequestError(ref err) => Some(err),
            ImlManagerCliError::TokioTimerError(ref err) => Some(err),
            ImlManagerCliError::IntParseError(ref err) => Some(err),
            ImlManagerCliError::ParseDurationError(ref err) => Some(err),
        }
    }
}

impl From<std::num::ParseIntError> for ImlManagerCliError {
    fn from(err: std::num::ParseIntError) -> Self {
        ImlManagerCliError::IntParseError(err)
    }
}

impl From<DurationParseError> for ImlManagerCliError {
    fn from(err: DurationParseError) -> Self {
        ImlManagerCliError::ParseDurationError(err)
    }
}

impl From<tokio::timer::Error> for ImlManagerCliError {
    fn from(err: tokio::timer::Error) -> Self {
        ImlManagerCliError::TokioTimerError(err)
    }
}

impl From<iml_manager_client::ImlManagerClientError> for ImlManagerCliError {
    fn from(err: iml_manager_client::ImlManagerClientError) -> Self {
        ImlManagerCliError::ClientRequestError(err)
    }
}
