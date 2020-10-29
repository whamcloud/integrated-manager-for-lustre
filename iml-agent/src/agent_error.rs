// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use iml_fs::ImlFsError;
use iml_wire_types::PluginName;
use std::{fmt, process::Output};
use thiserror::Error;
use tokio_util::codec::LinesCodecError;

pub type Result<T> = std::result::Result<T, ImlAgentError>;

#[derive(Debug)]
pub struct NoSessionError(pub PluginName);

impl fmt::Display for NoSessionError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "No session found for {:?}", self.0)
    }
}

impl std::error::Error for NoSessionError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

#[derive(Debug)]
pub struct NoPluginError(pub PluginName);

impl fmt::Display for NoPluginError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "Plugin in registry not found for {:?}", self.0)
    }
}

impl std::error::Error for NoPluginError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

#[derive(Debug)]
pub struct RequiredError(pub String);

impl fmt::Display for RequiredError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{:?}", self.0)
    }
}

impl std::error::Error for RequiredError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

#[derive(Debug)]
pub struct CibError(pub String);

impl fmt::Display for CibError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for CibError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

#[derive(Debug, Error)]
pub enum ImlAgentError {
    #[error(transparent)]
    AddrParseError(#[from] std::net::AddrParseError),
    #[error(transparent)]
    IpNetworkError(#[from] ipnetwork::IpNetworkError),
    #[error(transparent)]
    CibError(#[from] CibError),
    #[error(transparent)]
    CmdError(#[from] CmdError),
    #[error(transparent)]
    FmtError(#[from] strfmt::FmtError),
    #[error(transparent)]
    FromUtf8Error(#[from] std::string::FromUtf8Error),
    #[error(transparent)]
    ImlFsError(#[from] ImlFsError),
    #[error(transparent)]
    InvalidHeaderValue(#[from] http::header::InvalidHeaderValue),
    #[error(transparent)]
    InvalidUri(#[from] http::uri::InvalidUri),
    #[error(transparent)]
    InvalidUriParts(#[from] http::uri::InvalidUriParts),
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    LiblustreError(#[from] liblustreapi::error::LiblustreError),
    #[error(transparent)]
    LinesCodecError(#[from] LinesCodecError),
    #[error(transparent)]
    LustreCollectorError(#[from] lustre_collector::error::LustreCollectorError),
    #[error("Marker Not Found")]
    MarkerNotFound,
    #[error("Argument '{0}' Missing")]
    MissingArgument(String),
    #[error(transparent)]
    NoPluginError(#[from] NoPluginError),
    #[error(transparent)]
    NoSessionError(#[from] NoSessionError),
    #[error(transparent)]
    OneshotCanceled(#[from] futures::channel::oneshot::Canceled),
    #[error(transparent)]
    ParseBoolError(#[from] std::str::ParseBoolError),
    #[error(transparent)]
    ParseIntError(#[from] std::num::ParseIntError),
    #[error(transparent)]
    RequiredError(#[from] RequiredError),
    #[error(transparent)]
    Reqwest(#[from] reqwest::Error),
    #[error("Rx went away")]
    SendError,
    #[error(transparent)]
    Serde(#[from] serde_json::Error),
    #[error(transparent)]
    SystemdError(#[from] iml_systemd::SystemdError),
    #[error(transparent)]
    TokioJoinError(#[from] tokio::task::JoinError),
    #[error(transparent)]
    TokioTimerError(#[from] tokio::time::Error),
    #[error("Unexpected status code")]
    UnexpectedStatusError,
    #[error(transparent)]
    UrlParseError(#[from] url::ParseError),
    #[error(transparent)]
    Utf8Error(#[from] std::str::Utf8Error),
    #[error(transparent)]
    XmlError(#[from] elementtree::Error),
    #[error(transparent)]
    QuickXmlError(#[from] quick_xml::Error),
    #[error("{0}")]
    LdevEntriesError(String),
    #[error(transparent)]
    CombineEasyError(#[from] combine::stream::easy::Errors<char, String, usize>),
}

impl From<Output> for ImlAgentError {
    fn from(output: Output) -> Self {
        ImlAgentError::CmdError(output.into())
    }
}

impl From<futures::channel::mpsc::SendError> for ImlAgentError {
    fn from(_: futures::channel::mpsc::SendError) -> Self {
        ImlAgentError::SendError
    }
}

impl serde::Serialize for ImlAgentError {
    fn serialize<S>(&self, serializer: S) -> std::result::Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&format!("{:?}", self))
    }
}
