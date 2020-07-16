// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future, Stream, StreamExt, TryFutureExt, TryStreamExt};
use iml_rabbit::{basic_consume, connect_to_queue, BasicConsumeOptions, Channel, ImlRabbitError};
use iml_wire_types::{Fqdn, PluginMessage};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ImlServiceQueueError {
    #[error(transparent)]
    ImlRabbitError(#[from] ImlRabbitError),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::error::Error),
}

/// Creates a consumer for an iml-service.
///
/// This is expected to be called once during startup.
pub async fn consume_service_queue<'a>(
    ch: &Channel,
    name: &'a str,
) -> Result<
    impl Stream<Item = Result<PluginMessage, ImlServiceQueueError>> + 'a,
    ImlServiceQueueError,
> {
    let q = connect_to_queue(name.to_string(), ch).await?;

    let s = basic_consume(
        ch,
        q,
        name,
        Some(BasicConsumeOptions {
            no_ack: true,
            ..BasicConsumeOptions::default()
        }),
    )
    .await?
    .map_err(ImlServiceQueueError::from)
    .map_ok(|(_, x)| x)
    .and_then(|m| {
        tracing::debug!("Incoming message: {}", String::from_utf8_lossy(&m.data));

        future::ready(serde_json::from_slice(&m.data).map_err(ImlServiceQueueError::from))
    });

    Ok(s)
}

/// Given an incoming message Return an `Option` of fqdn and body
pub fn data_only(message: PluginMessage) -> Option<(Fqdn, serde_json::Value)> {
    match message {
        PluginMessage::Data { body, fqdn, .. } => Some((fqdn, body)),
        _ => None,
    }
}

pub fn into_deserialized<T: serde::de::DeserializeOwned>(
    (fqdn, body): (Fqdn, serde_json::Value),
) -> Result<(Fqdn, T), ImlServiceQueueError> {
    let v = serde_json::from_value(body)?;

    Ok((fqdn, v))
}

pub fn consume_data<'a, T: serde::de::DeserializeOwned + Send + 'a>(
    ch: &'a Channel,
    queue_name: &'a str,
) -> impl Stream<Item = Result<(Fqdn, T), ImlServiceQueueError>> + 'a {
    consume_service_queue(ch, queue_name)
        .try_flatten_stream()
        .try_filter_map(|x| future::ok(data_only(x)))
        .and_then(|x| future::ready(into_deserialized(x)))
        .boxed()
}
