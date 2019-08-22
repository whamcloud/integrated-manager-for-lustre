// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    env,
    http_comms::{crypto_client, hyper_client},
};
use futures::{Future, IntoFuture, Stream};
use hyper::{header::HeaderValue, Body, Method, Request, StatusCode};
use tracing::debug;

/// Streams the given data to the manager mailbox.
pub fn send(
    message_name: String,
    stream: impl Stream<Item = bytes::Bytes, Error = ImlAgentError> + Send + 'static,
) -> impl Future<Item = (), Error = ImlAgentError> {
    let body = Body::wrap_stream(stream);
    let mut req = Request::new(body);
    *req.method_mut() = Method::POST;

    debug!("Sending mailbox message to {}", message_name);

    hyper_client::build_https_client(&env::PFX)
        .into_future()
        .and_then(move |c| {
            *req.uri_mut() = env::MANAGER_URL.join("/mailbox/")?.into_string().parse()?;
            req.headers_mut().insert(
                "mailbox-message-name",
                HeaderValue::from_str(&message_name)?,
            );

            Ok((c, req))
        })
        .and_then(|(c, req)| c.request(req).from_err())
        .and_then(|resp| {
            if resp.status() != StatusCode::CREATED {
                Err(ImlAgentError::UnexpectedStatusError)
            } else {
                debug!("Mailbox message sent");
                Ok(())
            }
        })
}

/// Retrieves the given data from the manager mailbox as a `Stream`
/// of line-delimited `String`
pub fn get(message_name: String) -> impl Stream<Item = String, Error = ImlAgentError> {
    let q: Vec<(String, String)> = vec![];

    crypto_client::get_id(&env::PFX)
        .into_future()
        .from_err()
        .and_then(crypto_client::create_client)
        .and_then(move |client| {
            let message_endpoint = env::MANAGER_URL.join("/mailbox/")?.join(&message_name)?;

            Ok((client, message_endpoint))
        })
        .map(move |(client, message_endpoint)| {
            stream_lines::strings(crypto_client::get_stream(&client, message_endpoint, &q))
        })
        .flatten_stream()
}
