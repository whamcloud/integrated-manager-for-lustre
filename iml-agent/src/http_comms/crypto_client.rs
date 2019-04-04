// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::{ImlAgentError, Result};
use futures::{future::Future, IntoFuture, Stream};
use reqwest::{
    r#async::{Chunk, Client, Decoder, Response},
    Identity, IntoUrl,
};
use std::{mem, time::Duration};

/// Creates an `Identity` from the given pfx buffer
///
/// # Arguments
///
/// * `pfx` - The incoming pfx buffer
pub fn get_id(pfx: &[u8]) -> Result<Identity> {
    Identity::from_pkcs12_der(pfx, "").map_err(ImlAgentError::Reqwest)
}

/// Creates a client that is authenticated to
/// communicate with the manager.
///
/// # Arguments
///
/// * `id` - The client identity to use
pub fn create_client(id: Identity) -> Result<Client> {
    Client::builder()
        .danger_accept_invalid_certs(true)
        .identity(id)
        .timeout(Duration::from_secs(60))
        .build()
        .map_err(ImlAgentError::Reqwest)
}

/// Performs a GET with the given `client`, to the given `url`.
///
/// # Arguments
///
/// * `client` - The client used to perform request.
/// * `url` - The url to request from.
/// * `query` - An object to build a query string
pub fn get(
    client: &Client,
    url: impl IntoUrl,
    query: &(impl serde::Serialize + ?Sized),
) -> impl Future<Item = Chunk, Error = ImlAgentError> {
    client
        .get(url)
        .query(query)
        .send()
        .map_err(ImlAgentError::Reqwest)
        .and_then(handle_resp)
}

/// Performs a POST with the given `client`, to the given `url`.
///
/// # Arguments
///
/// * `client` - The client used to perform request.
/// * `url` - The url to request from.
/// * `json` - An arbitrary type that can be serialized by serde.
pub fn post<T: serde::Serialize + Sized>(
    client: &Client,
    url: impl IntoUrl,
    json: &T,
) -> impl Future<Item = Chunk, Error = ImlAgentError> {
    client
        .post(url)
        .json(json)
        .send()
        .map_err(ImlAgentError::Reqwest)
        .and_then(handle_resp)
}

/// Handles an incoming response. Returns a future of the buffered body
///
/// # Arguments
///
/// * - `resp` - The Response to handle
fn handle_resp(resp: Response) -> impl Future<Item = Chunk, Error = ImlAgentError> {
    resp.error_for_status()
        .into_future()
        .map_err(ImlAgentError::Reqwest)
        .and_then(|mut res| {
            let body = mem::replace(res.body_mut(), Decoder::empty());
            body.concat2().map_err(ImlAgentError::Reqwest)
        })
}

#[cfg(test)]
mod tests {
    use super::{get, post};
    use crate::agent_error::Result;
    use mockito::mock;
    use pretty_assertions::assert_eq;
    use reqwest::r#async::Client;
    use std::str;
    use tokio::runtime::Runtime;
    use url::Url;

    fn create_url() -> Result<Url> {
        Ok(Url::parse(&mockito::server_url())?.join("/agent/message")?)
    }

    #[test]
    fn test_get() -> Result<()> {
        let m = mock("GET", "/agent/message?server_boot_time=2019-02-13T13%3A26%3A28.000000%2B00%3A00Z&client_start_time=2019-02-14T02%3A04%3A33.057646%2B00%3A00Z")
            .with_status(200)
            .with_header("content-type", "text/plain")
            .with_body("foo")
            .create();

        let url = create_url()?;

        let query = &[
            ("server_boot_time", "2019-02-13T13:26:28.000000+00:00Z"),
            ("client_start_time", "2019-02-14T02:04:33.057646+00:00Z"),
        ];

        let r = Runtime::new()
            .unwrap()
            .block_on_all(get(&Client::new(), url, query))?;

        assert_eq!(str::from_utf8(r.as_ref())?, "foo");

        m.assert();

        Ok(())
    }

    #[test]
    fn test_post() -> Result<()> {
        let m = mock("POST", "/agent/message")
            .with_status(201)
            .with_header("content-type", "application/json")
            .with_body("{}")
            .create();

        let url = create_url()?;

        #[derive(serde::Serialize)]
        struct Foo {}

        let r = Runtime::new()
            .unwrap()
            .block_on_all(post(&Client::new(), url, &Foo {}))?;

        assert_eq!(str::from_utf8(r.as_ref())?, "{}");

        m.assert();

        Ok(())
    }
}
