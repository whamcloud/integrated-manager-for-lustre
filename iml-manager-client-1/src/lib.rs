// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::future::{FutureExt, TryFutureExt};
pub use reqwest::{header, Client, Response, StatusCode, Url};
use serde::de::DeserializeOwned;
use std::{fmt::Debug, pin::Pin, time::Duration};
use tokio01::executor::Executor;

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

pub struct DefaultExecutor(pub tokio01::executor::DefaultExecutor);

impl tokio::executor::Executor for DefaultExecutor {
    fn spawn(
        &mut self,
        future: Pin<Box<dyn futures::Future<Output = ()> + Send>>,
    ) -> Result<(), tokio::executor::SpawnError> {
        self.0
            .spawn(Box::new(future.unit_error().boxed().compat()))
            .map_err(|e: tokio01::executor::SpawnError| {
                if e.is_shutdown() {
                    tokio::executor::SpawnError::shutdown()
                } else {
                    tokio::executor::SpawnError::at_capacity()
                }
            })
    }

    fn status(&self) -> Result<(), tokio::executor::SpawnError> {
        self.0.status().map_err(|e: tokio01::executor::SpawnError| {
            if e.is_shutdown() {
                tokio::executor::SpawnError::shutdown()
            } else {
                tokio::executor::SpawnError::at_capacity()
            }
        })
    }
}

impl tokio::executor::Executor for &DefaultExecutor {
    fn spawn(
        &mut self,
        future: Pin<Box<dyn futures::Future<Output = ()> + Send>>,
    ) -> Result<(), tokio::executor::SpawnError> {
        tokio01::executor::DefaultExecutor::current()
            .spawn(Box::new(future.unit_error().boxed().compat()))
            .map_err(|e: tokio01::executor::SpawnError| {
                if e.is_shutdown() {
                    tokio::executor::SpawnError::shutdown()
                } else {
                    tokio::executor::SpawnError::at_capacity()
                }
            })
    }

    fn status(&self) -> Result<(), tokio::executor::SpawnError> {
        self.0.status().map_err(|e: tokio01::executor::SpawnError| {
            if e.is_shutdown() {
                tokio::executor::SpawnError::shutdown()
            } else {
                tokio::executor::SpawnError::at_capacity()
            }
        })
    }
}

/// Get a client that is able to make authenticated requests
/// against the API
pub fn get_client(executor: Option<DefaultExecutor>) -> Result<Client, ImlManagerClientError> {
    let header_value = header::HeaderValue::from_str(&format!(
        "ApiKey {}:{}",
        iml_manager_env::get_api_user(),
        iml_manager_env::get_api_key()
    ))?;

    let headers = vec![(header::AUTHORIZATION, header_value)]
        .into_iter()
        .collect();

    let builder = Client::builder()
        .http2_prior_knowledge()
        .default_headers(headers)
        .danger_accept_invalid_certs(true);

    let builder = if let Some(executor) = executor {
        builder.executor(executor)
    } else {
        builder
    };

    builder.build().map_err(ImlManagerClientError::Reqwest)
}

/// Given a path, constructs a full API url
fn create_api_url(path: impl ToString) -> Result<Url, ImlManagerClientError> {
    let mut path = path.to_string();

    if !path.ends_with('/') {
        path.push('/');
    }

    if path.starts_with('/') {
        path = path[1..].into();
    };

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
    tracing::debug!("GET to {}", path.to_string());

    let uri = create_api_url(path)?;
    tracing::info!("uri: {}", uri);

    let resp = client
        .get(uri)
        .query(&query)
        .send()
        .await?
        .error_for_status()?;
    tracing::info!("resp: {:#?}", resp);

    let json = resp.json().await?;

    tracing::debug!("Resp: {:?}", json);

    Ok(json)
}

/// Performs a POST to the given API path
pub async fn post(
    client: Client,
    path: &str,
    body: impl serde::Serialize,
) -> Result<Response, ImlManagerClientError> {
    let uri = create_api_url(path)?;

    let resp = client
        .post(uri)
        .json(&body)
        .send()
        .await?
        .error_for_status()?;

    tracing::debug!("Resp: {:?}", resp);

    Ok(resp)
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
