// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::PluginName;
use std::{fmt, process::Output};

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
pub enum ImlAgentError {
    Io(std::io::Error),
    Serde(serde_json::Error),
    Reqwest(reqwest::Error),
    UrlParseError(url::ParseError),
    Utf8Error(std::str::Utf8Error),
    FromUtf8Error(std::string::FromUtf8Error),
    TokioTimerError(tokio::timer::Error),
    AddrParseError(std::net::AddrParseError),
    ParseIntError(std::num::ParseIntError),
    NoSessionError(NoSessionError),
    NoPluginError(NoPluginError),
    RequiredError(RequiredError),
    OneshotCanceled(futures01::sync::oneshot::Canceled),
    LiblustreError(liblustreapi::error::LiblustreError),
    CmdOutputError(Output),
    SendError,
    InvalidUriParts(http::uri::InvalidUriParts),
    InvalidUri(http::uri::InvalidUri),
    InvalidHeaderValue(http::header::InvalidHeaderValue),
    HyperError(hyper::error::Error),
    NativeTls(native_tls::Error),
    XmlError(elementtree::Error),
    UnexpectedStatusError,
}

impl std::fmt::Display for ImlAgentError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlAgentError::Io(ref err) => write!(f, "{}", err),
            ImlAgentError::Serde(ref err) => write!(f, "{}", err),
            ImlAgentError::Reqwest(ref err) => write!(f, "{}", err),
            ImlAgentError::UrlParseError(ref err) => write!(f, "{}", err),
            ImlAgentError::Utf8Error(ref err) => write!(f, "{}", err),
            ImlAgentError::FromUtf8Error(ref err) => write!(f, "{}", err),
            ImlAgentError::TokioTimerError(ref err) => write!(f, "{}", err),
            ImlAgentError::AddrParseError(ref err) => write!(f, "{}", err),
            ImlAgentError::ParseIntError(ref err) => write!(f, "{}", err),
            ImlAgentError::NoSessionError(ref err) => write!(f, "{}", err),
            ImlAgentError::NoPluginError(ref err) => write!(f, "{}", err),
            ImlAgentError::RequiredError(ref err) => write!(f, "{}", err),
            ImlAgentError::OneshotCanceled(ref err) => write!(f, "{}", err),
            ImlAgentError::LiblustreError(ref err) => write!(f, "{}", err),

            ImlAgentError::CmdOutputError(ref err) => write!(
                f,
                "{}, stdout: {}, stderr: {}",
                err.status,
                String::from_utf8_lossy(&err.stdout),
                String::from_utf8_lossy(&err.stderr)
            ),
            ImlAgentError::SendError => write!(f, "Rx went away"),
            ImlAgentError::InvalidUriParts(ref err) => write!(f, "{}", err),
            ImlAgentError::InvalidUri(ref err) => write!(f, "{}", err),
            ImlAgentError::InvalidHeaderValue(ref err) => write!(f, "{}", err),
            ImlAgentError::HyperError(ref err) => write!(f, "{}", err),
            ImlAgentError::NativeTls(ref err) => write!(f, "{}", err),
            ImlAgentError::XmlError(ref err) => write!(f, "{}", err),
            ImlAgentError::UnexpectedStatusError => write!(f, "Unexpected status code"),
        }
    }
}

impl std::error::Error for ImlAgentError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlAgentError::Io(ref err) => Some(err),
            ImlAgentError::Serde(ref err) => Some(err),
            ImlAgentError::Reqwest(ref err) => Some(err),
            ImlAgentError::UrlParseError(ref err) => Some(err),
            ImlAgentError::Utf8Error(ref err) => Some(err),
            ImlAgentError::FromUtf8Error(ref err) => Some(err),
            ImlAgentError::TokioTimerError(ref err) => Some(err),
            ImlAgentError::AddrParseError(ref err) => Some(err),
            ImlAgentError::ParseIntError(ref err) => Some(err),
            ImlAgentError::NoSessionError(ref err) => Some(err),
            ImlAgentError::NoPluginError(ref err) => Some(err),
            ImlAgentError::RequiredError(ref err) => Some(err),
            ImlAgentError::OneshotCanceled(ref err) => Some(err),
            ImlAgentError::LiblustreError(ref err) => Some(err),

            ImlAgentError::CmdOutputError(_) => None,
            ImlAgentError::SendError => None,
            ImlAgentError::InvalidUriParts(ref err) => Some(err),
            ImlAgentError::InvalidUri(ref err) => Some(err),
            ImlAgentError::InvalidHeaderValue(ref err) => Some(err),
            ImlAgentError::HyperError(ref err) => Some(err),
            ImlAgentError::NativeTls(ref err) => Some(err),
            ImlAgentError::XmlError(ref err) => Some(err),
            ImlAgentError::UnexpectedStatusError => None,
        }
    }
}

impl From<std::io::Error> for ImlAgentError {
    fn from(err: std::io::Error) -> Self {
        ImlAgentError::Io(err)
    }
}

impl From<serde_json::Error> for ImlAgentError {
    fn from(err: serde_json::Error) -> Self {
        ImlAgentError::Serde(err)
    }
}

impl From<reqwest::Error> for ImlAgentError {
    fn from(err: reqwest::Error) -> Self {
        ImlAgentError::Reqwest(err)
    }
}

impl From<url::ParseError> for ImlAgentError {
    fn from(err: url::ParseError) -> Self {
        ImlAgentError::UrlParseError(err)
    }
}

impl From<std::str::Utf8Error> for ImlAgentError {
    fn from(err: std::str::Utf8Error) -> Self {
        ImlAgentError::Utf8Error(err)
    }
}

impl From<std::string::FromUtf8Error> for ImlAgentError {
    fn from(err: std::string::FromUtf8Error) -> Self {
        ImlAgentError::FromUtf8Error(err)
    }
}

impl From<tokio::timer::Error> for ImlAgentError {
    fn from(err: tokio::timer::Error) -> Self {
        ImlAgentError::TokioTimerError(err)
    }
}

impl From<dns_lookup::LookupError> for ImlAgentError {
    fn from(err: dns_lookup::LookupError) -> Self {
        ImlAgentError::Io(err.into())
    }
}

impl From<std::net::AddrParseError> for ImlAgentError {
    fn from(err: std::net::AddrParseError) -> Self {
        ImlAgentError::AddrParseError(err)
    }
}

impl From<std::num::ParseIntError> for ImlAgentError {
    fn from(err: std::num::ParseIntError) -> Self {
        ImlAgentError::ParseIntError(err)
    }
}

impl From<NoSessionError> for ImlAgentError {
    fn from(err: NoSessionError) -> Self {
        ImlAgentError::NoSessionError(err)
    }
}

impl From<NoPluginError> for ImlAgentError {
    fn from(err: NoPluginError) -> Self {
        ImlAgentError::NoPluginError(err)
    }
}

impl From<liblustreapi::error::LiblustreError> for ImlAgentError {
    fn from(err: liblustreapi::error::LiblustreError) -> Self {
        ImlAgentError::LiblustreError(err)
    }
}

impl From<Output> for ImlAgentError {
    fn from(output: Output) -> Self {
        ImlAgentError::CmdOutputError(output)
    }
}

impl From<RequiredError> for ImlAgentError {
    fn from(err: RequiredError) -> Self {
        ImlAgentError::RequiredError(err)
    }
}

impl From<futures01::sync::oneshot::Canceled> for ImlAgentError {
    fn from(err: futures01::sync::oneshot::Canceled) -> Self {
        ImlAgentError::OneshotCanceled(err)
    }
}

impl<T> From<futures01::sync::mpsc::SendError<T>> for ImlAgentError {
    fn from(_: futures01::sync::mpsc::SendError<T>) -> Self {
        ImlAgentError::SendError
    }
}

impl From<http::uri::InvalidUriParts> for ImlAgentError {
    fn from(err: http::uri::InvalidUriParts) -> Self {
        ImlAgentError::InvalidUriParts(err)
    }
}

impl From<http::uri::InvalidUri> for ImlAgentError {
    fn from(err: http::uri::InvalidUri) -> Self {
        ImlAgentError::InvalidUri(err)
    }
}

impl From<hyper::error::Error> for ImlAgentError {
    fn from(err: hyper::error::Error) -> Self {
        ImlAgentError::HyperError(err)
    }
}

impl From<native_tls::Error> for ImlAgentError {
    fn from(err: native_tls::Error) -> Self {
        ImlAgentError::NativeTls(err)
    }
}

impl From<elementtree::Error> for ImlAgentError {
    fn from(err: elementtree::Error) -> Self {
        ImlAgentError::XmlError(err)
    }
}

impl From<http::header::InvalidHeaderValue> for ImlAgentError {
    fn from(err: http::header::InvalidHeaderValue) -> Self {
        ImlAgentError::InvalidHeaderValue(err)
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
