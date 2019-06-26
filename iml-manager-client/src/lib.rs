// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{Future, IntoFuture as _, Stream as _};
use reqwest::{
    header,
    r#async::{Chunk, Client, Decoder, Response},
    Url,
};
use serde::de::DeserializeOwned;
use std::{fmt::Debug, mem, time::Duration};

#[derive(Debug)]
pub enum ImlManagerClientError {
    Reqwest(reqwest::Error),
    InvalidHeaderValue(reqwest::header::InvalidHeaderValue),
    UrlParseError(url::ParseError),
    SerdeJsonError(serde_json::error::Error),
}

impl std::fmt::Display for ImlManagerClientError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlManagerClientError::Reqwest(ref err) => write!(f, "{}", err),
            ImlManagerClientError::InvalidHeaderValue(ref err) => write!(f, "{}", err),
            ImlManagerClientError::UrlParseError(ref err) => write!(f, "{}", err),
            ImlManagerClientError::SerdeJsonError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlManagerClientError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlManagerClientError::Reqwest(ref err) => Some(err),
            ImlManagerClientError::InvalidHeaderValue(ref err) => Some(err),
            ImlManagerClientError::UrlParseError(ref err) => Some(err),
            ImlManagerClientError::SerdeJsonError(ref err) => Some(err),
        }
    }
}

impl From<reqwest::Error> for ImlManagerClientError {
    fn from(err: reqwest::Error) -> Self {
        ImlManagerClientError::Reqwest(err)
    }
}

impl From<reqwest::header::InvalidHeaderValue> for ImlManagerClientError {
    fn from(err: reqwest::header::InvalidHeaderValue) -> Self {
        ImlManagerClientError::InvalidHeaderValue(err)
    }
}

impl From<url::ParseError> for ImlManagerClientError {
    fn from(err: url::ParseError) -> Self {
        ImlManagerClientError::UrlParseError(err)
    }
}

impl From<serde_json::error::Error> for ImlManagerClientError {
    fn from(err: serde_json::error::Error) -> Self {
        ImlManagerClientError::SerdeJsonError(err)
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone)]
#[serde(rename_all = "snake_case")]
pub enum RunStratagemCommandResult {
    FilesystemRequired,
    DurationOrderError,
    FilesystemDoesNotExist,
    StratagemServerProfileNotInstalled,
    ServerError,
    UnknownError
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct RunStratagemValidationError {
    pub code: RunStratagemCommandResult,
    pub message: String,
}

impl std::fmt::Display for RunStratagemValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for  RunStratagemValidationError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

/// Get a client that is able to make authenticated requests
/// against the API
pub fn get_client() -> Result<Client, ImlManagerClientError> {
    let header_value = header::HeaderValue::from_str(&format!(
        "ApiKey {}:{}",
        iml_manager_env::get_api_user(),
        iml_manager_env::get_api_key()
    ))?;

    let headers = [(header::AUTHORIZATION, header_value)]
        .iter()
        .cloned()
        .collect();

    Client::builder()
        .timeout(Duration::from_secs(60))
        .default_headers(headers)
        .danger_accept_invalid_certs(true)
        .build()
        .map_err(ImlManagerClientError::Reqwest)
}

/// Given a path, constructs a full API url
fn create_api_url(path: &str) -> Result<Url, ImlManagerClientError> {
    let path = if !path.ends_with('/') {
        format!("{}/", path)
    } else {
        path.to_string()
    };

    let mut url = Url::parse(&iml_manager_env::get_manager_url())?
        .join("/api/")?
        .join(&path)?;

    url.set_query(Some("limit=0"));

    Ok(url)
}

/// Performs a GET to the given API path
pub fn get<T: DeserializeOwned + Debug>(
    client: Client,
    path: &str,
) -> impl Future<Item = T, Error = ImlManagerClientError> {
    log::debug!("GET to {:?}", path);

    create_api_url(path).into_future().and_then(move |url| {
        client
            .get(url)
            .send()
            .from_err()
            .and_then(|mut res| res.json())
            .from_err()
            .inspect(|x| log::debug!("Resp: {:?}", x))
    })
}

/// Handles an incoming response. Returns a future of the buffered body
///
/// # Arguments
///
/// * - `resp` - The Response to handle
pub fn concat_body(
    mut resp: Response,
) -> impl Future<Item = (Response, Chunk), Error = ImlManagerClientError> {
    let body = mem::replace(resp.body_mut(), Decoder::empty());
    body.concat2().map(move |chunk| (resp, chunk)).from_err()
}

/// Performs a POST to the given API path
pub fn post(
    client: Client,
    path: &str,
    body: impl serde::Serialize,
) -> impl Future<Item = Response, Error = ImlManagerClientError> {
    create_api_url(path)
        .into_future()
        .and_then(move |url| client.post(url).json(&body).send().from_err())
}
