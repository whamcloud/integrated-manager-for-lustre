// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env, http_comms::crypto_client};
use futures::{future, Stream, TryFutureExt, TryStreamExt};
use iml_fs::read_lines;
use reqwest::{Body, StatusCode};

/// Streams the given data to the manager mailbox.
pub async fn send(
    message_name: String,
    stream: impl Stream<Item = Result<bytes::Bytes, ImlAgentError>> + Send + Sync + 'static,
) -> Result<(), ImlAgentError> {
    tracing::debug!("Sending mailbox message to {}", message_name);

    let id = crypto_client::get_id(&env::PFX)?;
    let client = crypto_client::create_client(id)?;

    let body = Body::wrap_stream(stream);

    let resp = client
        .post(env::MANAGER_URL.join("/mailbox/")?)
        .header("mailbox-message-name", &message_name)
        .body(body)
        .send()
        .await?;

    if resp.status() != StatusCode::CREATED {
        Err(ImlAgentError::UnexpectedStatusError)
    } else {
        tracing::debug!("Mailbox message sent");
        Ok(())
    }
}

/// Retrieves the given data from the manager mailbox as a `Stream`
/// of line-delimited `String`
pub fn get(message_name: String) -> impl Stream<Item = Result<String, ImlAgentError>> {
    let q: Vec<(String, String)> = vec![];

    future::ready(crypto_client::get_id(&env::PFX))
        .err_into()
        .and_then(|id| async { crypto_client::create_client(id) })
        .and_then(move |client| {
            async move {
                let message_endpoint = env::MANAGER_URL.join("/mailbox/")?.join(&message_name)?;

                Ok((client, message_endpoint))
            }
        })
        .map_ok(move |(client, message_endpoint)| {
            read_lines(crypto_client::get_stream(&client, message_endpoint, &q)).err_into()
        })
        .try_flatten_stream()
}
