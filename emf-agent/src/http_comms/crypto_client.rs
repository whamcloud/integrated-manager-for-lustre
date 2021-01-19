// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use bytes::Bytes;
use futures::{stream, Future, Stream, TryFutureExt, TryStreamExt};
use reqwest::{Client, Identity, IntoUrl, Response};
use std::time::Duration;

/// Creates an `Identity` from the given pem buffer
///
/// # Arguments
///
/// * `pem` - The incoming pem buffer
pub fn get_id(pem: &[u8]) -> Result<Identity, EmfAgentError> {
    Identity::from_pem(pem).map_err(EmfAgentError::Reqwest)
}

/// Creates a client that is authenticated to
/// communicate with the manager.
///
/// # Arguments
///
/// * `id` - The client identity to use
pub fn create_client(id: Identity) -> Result<Client, EmfAgentError> {
    Client::builder()
        .use_rustls_tls()
        .danger_accept_invalid_certs(true)
        .identity(id)
        .timeout(Duration::from_secs(900))
        .build()
        .map_err(EmfAgentError::Reqwest)
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
) -> impl Future<Output = Result<Response, EmfAgentError>> {
    client.get(url).query(query).send().err_into()
}

/// Performs a GET with the given `client`, to the given `url`.
/// Buffers the response into a `Chunk`
///
/// # Arguments
///
/// * `client` - The client used to perform request.
/// * `url` - The url to request from.
/// * `query` - An object to build a query string
pub fn get_buffered(
    client: &Client,
    url: impl IntoUrl,
    query: &(impl serde::Serialize + ?Sized),
) -> impl Future<Output = Result<String, EmfAgentError>> {
    get(client, url, query).and_then(handle_resp)
}

/// Performs a GET with the given `client`, to the given `url`.
/// Streams the response `Chunk`s
///
/// # Arguments
///
/// * `client` - The client used to perform request.
/// * `url` - The url to request from.
/// * `query` - An object to build a query string
pub fn get_stream(
    client: &Client,
    url: impl IntoUrl,
    query: &(impl serde::Serialize + ?Sized),
) -> impl Stream<Item = Result<Bytes, EmfAgentError>> {
    get(client, url, query)
        .inspect_ok(|resp| tracing::debug!("Get stream headers: {:?}", resp.headers()))
        .and_then(|resp| async { resp.error_for_status().map_err(|e| e.into()) })
        .map_ok(|resp| {
            stream::unfold(resp, |mut resp| async move {
                let result = resp.chunk().await;

                match result {
                    Ok(Some(chunk)) => Some((Ok(chunk), resp)),
                    Ok(None) => None,
                    Err(err) => Some((Err(err), resp)),
                }
            })
            .err_into()
        })
        .try_flatten_stream()
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
) -> impl Future<Output = Result<String, EmfAgentError>> {
    client
        .post(url)
        .json(json)
        .send()
        .map_err(EmfAgentError::Reqwest)
        .and_then(handle_resp)
}

/// Handles an incoming response. Returns a future of the buffered body
///
/// # Arguments
///
/// * - `resp` - The Response to handle
async fn handle_resp(resp: Response) -> Result<String, EmfAgentError> {
    let resp = resp.error_for_status()?;

    tracing::debug!("resp headers: {:?}", resp.headers());

    let text = resp.text().await?;

    Ok(text)
}

#[cfg(test)]
mod tests {
    use super::{get_buffered, get_stream, post};
    use crate::agent_error::EmfAgentError;
    use emf_fs::read_lines;
    use futures::TryStreamExt;
    use mockito::mock;
    use reqwest::Client;
    use std::str;
    use url::Url;

    fn create_url() -> Result<Url, EmfAgentError> {
        Ok(Url::parse(&mockito::server_url())?.join("/agent/message")?)
    }

    #[tokio::test]
    async fn test_get_buffered() -> Result<(), EmfAgentError> {
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

        let r = get_buffered(&Client::new(), url, query).await?;

        assert_eq!(str::from_utf8(r.as_ref())?, "foo");

        m.assert();

        Ok(())
    }

    #[tokio::test]
    async fn test_get_stream() -> Result<(), EmfAgentError> {
        let data = "1577893 [0x200000bd1:0x1397:0x0]
1579139 [0x200000bd1:0x1875:0x0]
1579140 [0x200000bd1:0x1876:0x0]
1579141 [0x200000bd1:0x1877:0x0]
1579142 [0x200000bd1:0x1878:0x0]
1579143 [0x200000bd1:0x1879:0x0]
1579163 [0x200000bd1:0x188d:0x0]
1579164 [0x200000bd1:0x188e:0x0]
1579165 [0x200000bd1:0x188f:0x0]
1579166 [0x200000bd1:0x1890:0x0]
1579167 [0x200000bd1:0x1891:0x0]
1579168 [0x200000bd1:0x1892:0x0]
1579169 [0x200000bd1:0x1893:0x0]
1579170 [0x200000bd1:0x1894:0x0]
1579171 [0x200000bd1:0x1895:0x0]
1579172 [0x200000bd1:0x1896:0x0]
1579173 [0x200000bd1:0x1897:0x0]
1579174 [0x200000bd1:0x1898:0x0]
1579175 [0x200000bd1:0x1899:0x0]
1579176 [0x200000bd1:0x189a:0x0]
1579177 [0x200000bd1:0x189b:0x0]
1579178 [0x200000bd1:0x189c:0x0]
1579179 [0x200000bd1:0x189d:0x0]
1579180 [0x200000bd1:0x189e:0x0]
1579181 [0x200000bd1:0x189f:0x0]
1579182 [0x200000bd1:0x18a0:0x0]
1579183 [0x200000bd1:0x18a1:0x0]";

        let m = mock("GET", "/agent/message?server_boot_time=2019-02-13T13%3A26%3A28.000000%2B00%3A00Z&client_start_time=2019-02-14T02%3A04%3A33.057646%2B00%3A00Z")
            .with_status(200)
            .with_header("content-type", "text/plain")
            .with_body(data)
            .create();

        let url = create_url()?;

        let query = &[
            ("server_boot_time", "2019-02-13T13:26:28.000000+00:00Z"),
            ("client_start_time", "2019-02-14T02:04:33.057646+00:00Z"),
        ];

        let s = get_stream(&Client::new(), url, query);
        let r: Vec<_> = read_lines(s).try_collect().await?;

        assert_eq!(r, data.split('\n').collect::<Vec<_>>());

        m.assert();

        Ok(())
    }

    #[tokio::test]
    async fn test_post() -> Result<(), EmfAgentError> {
        #[derive(serde::Serialize)]
        struct Foo {}

        let m = mock("POST", "/agent/message")
            .with_status(201)
            .with_header("content-type", "application/json")
            .with_body("{}")
            .create();

        let url = create_url()?;

        let r = post(&Client::new(), url, &Foo {}).await?;

        assert_eq!(str::from_utf8(r.as_ref())?, "{}");

        m.assert();

        Ok(())
    }
}
