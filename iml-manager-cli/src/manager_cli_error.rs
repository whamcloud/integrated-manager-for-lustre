// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, PartialEq, Eq)]
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

impl std::error::Error for DurationParseError {
    fn description(&self) -> &str {
        match self {
            DurationParseError::NoUnit => "No unit specified.",
            DurationParseError::InvalidUnit => "Invalid unit. Valid units include 'h' and 'd'.",
            DurationParseError::InvalidValue => "Invalid value specified. Must be a valid integer.",
        }
    }
}

#[derive(Debug)]
pub enum ImlManagerCliError {
    Reqwest(reqwest::Error),
    InvalidHeaderValue(reqwest::header::InvalidHeaderValue),
    TokioTimerError(tokio::timer::Error),
    UrlParseError(url::ParseError),
    IntParseError(std::num::ParseIntError),
    ParseDurationError(DurationParseError),
}

impl std::fmt::Display for ImlManagerCliError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlManagerCliError::Reqwest(ref err) => write!(f, "{}", err),
            ImlManagerCliError::InvalidHeaderValue(ref err) => write!(f, "{}", err),
            ImlManagerCliError::TokioTimerError(ref err) => write!(f, "{}", err),
            ImlManagerCliError::UrlParseError(ref err) => write!(f, "{}", err),
            ImlManagerCliError::IntParseError(ref err) => write!(f, "{}", err),
            ImlManagerCliError::ParseDurationError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlManagerCliError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlManagerCliError::Reqwest(ref err) => Some(err),
            ImlManagerCliError::InvalidHeaderValue(ref err) => Some(err),
            ImlManagerCliError::TokioTimerError(ref err) => Some(err),
            ImlManagerCliError::UrlParseError(ref err) => Some(err),
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

impl From<reqwest::Error> for ImlManagerCliError {
    fn from(err: reqwest::Error) -> Self {
        ImlManagerCliError::Reqwest(err)
    }
}

impl From<reqwest::header::InvalidHeaderValue> for ImlManagerCliError {
    fn from(err: reqwest::header::InvalidHeaderValue) -> Self {
        ImlManagerCliError::InvalidHeaderValue(err)
    }
}

impl From<url::ParseError> for ImlManagerCliError {
    fn from(err: url::ParseError) -> Self {
        ImlManagerCliError::UrlParseError(err)
    }
}
