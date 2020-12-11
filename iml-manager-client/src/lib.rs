// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_request_retry::{retry_future, RetryAction, RetryPolicy};
pub use reqwest::{header, Client, Response, StatusCode, Url};
use serde::de::DeserializeOwned;
use std::{fmt::Debug, path::Path, time::Duration};

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

/// Get a client that is able to make authenticated requests
/// against the API
pub fn get_api_client() -> Result<Client, ImlManagerClientError> {
    let header_value = header::HeaderValue::from_str(&format!(
        "ApiKey {}:{}",
        iml_manager_env::get_api_user(),
        iml_manager_env::get_api_key()
    ))?;

    let headers = vec![(header::AUTHORIZATION, header_value)]
        .into_iter()
        .collect();

    Client::builder()
        .timeout(Duration::from_secs(60))
        .default_headers(headers)
        .danger_accept_invalid_certs(true)
        .build()
        .map_err(ImlManagerClientError::Reqwest)
}

/// Get a client that is able to make non-authenticated requests
/// against the API
pub fn get_client() -> Result<Client, ImlManagerClientError> {
    Client::builder()
        .timeout(Duration::from_secs(60))
        .danger_accept_invalid_certs(true)
        .build()
        .map_err(ImlManagerClientError::Reqwest)
}

/// Given a path, constructs a url
pub fn create_url(path: impl ToString) -> Result<Url, ImlManagerClientError> {
    let path = path.to_string();

    let url = Url::parse(&iml_manager_env::get_manager_url())?
        .join("/")?
        .join(path.trim_start_matches('/'))?;

    Ok(url)
}

/// Given a path, constructs a full API url
pub fn create_api_url(path: impl ToString) -> Result<Url, ImlManagerClientError> {
    let mut path = path.to_string();

    let has_extension = Path::new(&path).extension().is_some();

    if !has_extension && !path.ends_with('/') {
        path.push('/');
    }

    if path.starts_with('/') {
        path = path[1..].into();
    };

    if path.starts_with("api/") {
        path = path[4..].into();
    }

    let url = Url::parse(&iml_manager_env::get_manager_url())?
        .join("/api/")?
        .join(&path)?;

    Ok(url)
}

/// Performs a GET to the given API path
pub async fn get<T: DeserializeOwned + Debug>(
    client: Client,
    path: impl ToString,
    query: impl serde::Serialize,
) -> Result<T, ImlManagerClientError> {
    tracing::debug!("GET to {} {}", path.to_string(), serde_json::json!(query));

    let uri = create_api_url(path)?;

    let resp = client
        .get(uri)
        .query(&query)
        .send()
        .await?
        .error_for_status()?;

    let json = resp.json().await?;

    tracing::debug!("Resp: {:?}", json);

    Ok(json)
}

/// Performs a GET to the influxdb
pub async fn get_influx<T: DeserializeOwned + Debug>(
    client: Client,
    db: &str,
    q: &str,
) -> Result<T, ImlManagerClientError> {
    let url = Url::parse(&iml_manager_env::get_manager_url())?.join("/influx")?;
    let resp = client
        .get(url)
        .query(&[("db", db), ("q", q)])
        .send()
        .await?
        .error_for_status()?;

    let json = resp.json().await?;

    tracing::debug!("Resp: {:?}", json);

    Ok(json)
}

fn create_policy<E: Debug>() -> impl RetryPolicy<E> {
    |k: u32, e| match k {
        0 => RetryAction::RetryNow,
        k if k < 3 => RetryAction::WaitFor(Duration::from_secs((2 * k) as u64)),
        _ => RetryAction::ReturnError(e),
    }
}

/// Performs a GET to the given API path.
/// If the request fails, this fn will retry 3 times,
/// sleeping between each attempt
pub async fn get_retry<T: DeserializeOwned + Debug>(
    client: Client,
    path: impl ToString,
    query: impl serde::Serialize,
) -> Result<T, ImlManagerClientError> {
    let client2 = client.clone();

    let policy = create_policy();

    let query = &query;

    retry_future(
        move |_| get(client2.clone(), path.to_string(), query),
        policy,
    )
    .await
}

/// Performs a POST to the given API path
/// This call will *not* treat unsuccessful status codes
/// as an error.
pub async fn post(
    client: Client,
    path: &str,
    body: impl serde::Serialize,
) -> Result<Response, ImlManagerClientError> {
    let uri = create_api_url(path)?;

    let resp = client.post(uri).json(&body).send().await?;

    tracing::debug!("Resp: {:?}", resp);

    Ok(resp)
}

/// Performs a POST request to the GraphQL endpoint
pub async fn graphql<T: DeserializeOwned + Debug>(
    client: Client,
    query: impl serde::Serialize + Debug,
) -> Result<T, ImlManagerClientError> {
    let url = Url::parse(&iml_manager_env::get_manager_url())?.join("/graphql")?;

    tracing::debug!("Sending GraphQL query: {:?}", query);

    let text = client
        .post(url)
        .json(&query)
        .send()
        .await?
        .error_for_status()?
        .text()
        .await?;

    tracing::debug!("GraphQL resp: {:?}", text);

    let json = serde_json::from_str(&text)?;

    Ok(json)
}

/// Performs a PUT to the given API path
pub async fn put(
    client: Client,
    path: &str,
    body: impl serde::Serialize,
) -> Result<Response, ImlManagerClientError> {
    let uri = create_api_url(path)?;

    Ok(client
        .put(uri)
        .json(&body)
        .send()
        .await?
        .error_for_status()?)
}

/// Performs a DELETE to the given API path
pub async fn delete(
    client: Client,
    path: &str,
    body: impl serde::Serialize,
) -> Result<Response, ImlManagerClientError> {
    let uri = create_api_url(path)?;

    Ok(client
        .delete(uri)
        .json(&body)
        .send()
        .await?
        .error_for_status()?)
}
