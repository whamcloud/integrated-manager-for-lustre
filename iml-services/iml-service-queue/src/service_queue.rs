// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future, Stream, StreamExt, TryFutureExt, TryStreamExt};
use iml_rabbit::{
    basic_consume, connect_to_queue, connect_to_rabbit, purge_queue, BasicConsumeOptions, Client,
    ImlRabbitError,
};
use iml_wire_types::{Fqdn, PluginMessage};

#[derive(Debug)]
pub enum ImlServiceQueueError {
    ImlRabbitError(ImlRabbitError),
    SerdeJsonError(serde_json::error::Error),
}

impl std::fmt::Display for ImlServiceQueueError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlServiceQueueError::ImlRabbitError(ref err) => write!(f, "{}", err),
            ImlServiceQueueError::SerdeJsonError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlServiceQueueError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlServiceQueueError::ImlRabbitError(ref err) => Some(err),
            ImlServiceQueueError::SerdeJsonError(ref err) => Some(err),
        }
    }
}

impl From<ImlRabbitError> for ImlServiceQueueError {
    fn from(err: ImlRabbitError) -> Self {
        ImlServiceQueueError::ImlRabbitError(err)
    }
}

impl From<serde_json::error::Error> for ImlServiceQueueError {
    fn from(err: serde_json::error::Error) -> Self {
        ImlServiceQueueError::SerdeJsonError(err)
    }
}

/// Creates a consumer for an iml-service.
/// This fn will first purge the queue
/// and then consume from it.
///
/// This is expected to be called once during startup.
pub fn consume_service_queue(
    client: Client,
    name: &'static str,
) -> impl Stream<Item = Result<PluginMessage, ImlServiceQueueError>> {
    let name2 = name.to_string();

    connect_to_queue(name.to_string(), client)
        .map_err(ImlServiceQueueError::from)
        .and_then(move |(c, q)| {
            async {
                let c = purge_queue(c, name2).await?;

                Ok((c, q))
            }
        })
        .and_then(move |(c, q)| {
            basic_consume(
                c,
                q,
                name,
                Some(BasicConsumeOptions {
                    no_ack: true,
                    ..BasicConsumeOptions::default()
                }),
            )
            .map_err(ImlServiceQueueError::from)
        })
        .map_ok(|s| s.map_err(ImlServiceQueueError::from))
        .try_flatten_stream()
        .and_then(|m| {
            tracing::debug!("Incoming message: {:?}", m.data);

            future::ready(serde_json::from_slice(&m.data).map_err(ImlServiceQueueError::from))
        })
        .boxed()
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

pub fn consume_data<T: serde::de::DeserializeOwned + Send + 'static>(
    queue_name: &'static str,
) -> impl Stream<Item = Result<(Fqdn, T), ImlServiceQueueError>> {
    connect_to_rabbit()
        .map_err(ImlServiceQueueError::from)
        .map_ok(move |client| consume_service_queue(client, queue_name))
        .try_flatten_stream()
        .try_filter_map(|x| future::ok(data_only(x)))
        .and_then(|x| future::ready(into_deserialized(x)))
        .boxed()
}
