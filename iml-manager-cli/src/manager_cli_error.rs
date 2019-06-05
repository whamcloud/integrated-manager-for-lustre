// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub type Result<T> = std::result::Result<T, ImlManagerCliError>;

#[derive(Debug)]
pub enum ImlManagerCliError {
    Reqwest(reqwest::Error),
    InvalidHeaderValue(reqwest::header::InvalidHeaderValue),
    TokioTimerError(tokio::timer::Error),
    UrlParseError(url::ParseError),
}

impl std::fmt::Display for ImlManagerCliError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlManagerCliError::Reqwest(ref err) => write!(f, "{}", err),
            ImlManagerCliError::InvalidHeaderValue(ref err) => write!(f, "{}", err),
            ImlManagerCliError::TokioTimerError(ref err) => write!(f, "{}", err),
            ImlManagerCliError::UrlParseError(ref err) => write!(f, "{}", err),
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
        }
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
