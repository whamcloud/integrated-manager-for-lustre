// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::manager_cli_error::ImlManagerCliError;
use futures::{Future, IntoFuture as _};
use reqwest::{header, r#async::Client, Url};
use serde::de::DeserializeOwned;
use std::{fmt::Debug, time::Duration};

/// Get a client that is able to make authenticated requests
/// against the API
pub fn get_client() -> Result<Client, ImlManagerCliError> {
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
        .map_err(ImlManagerCliError::Reqwest)
}

/// Given a path, constructs a full API url
fn create_api_url(path: &str) -> Result<Url, ImlManagerCliError> {
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
) -> impl Future<Item = T, Error = ImlManagerCliError> {
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
