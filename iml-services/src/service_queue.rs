// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_rabbit::{basic_consume, connect_to_queue, TcpClient};
use iml_wire_types::{Fqdn, PluginMessage};
use lapin_futures::channel::BasicConsumeOptions;
use tokio::prelude::*;

/// Creates a consumer for the locks queue.
/// This fn will first purge the locks queue
/// and then make a one-off request to get
/// all locks currently held in the job-scheduler.
///
/// This is expected to be called once during startup.
pub fn consume_service_queue(
    client: TcpClient,
    name: &'static str,
) -> impl Stream<Item = PluginMessage, Error = failure::Error> {
    connect_to_queue(name.to_string(), client)
        .and_then(move |(c, q)| {
            basic_consume(
                c,
                q,
                &name,
                Some(BasicConsumeOptions {
                    no_ack: true,
                    exclusive: true,
                    ..Default::default()
                }),
            )
        })
        .from_err()
        .map(|s| s.map_err(failure::Error::from))
        .flatten_stream()
        .and_then(|m| {
            log::trace!("Incoming message: {:?}", m.data);
            serde_json::from_slice(&m.data).map_err(failure::Error::from)
        })
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
) -> Result<(Fqdn, T), failure::Error> {
    let v = serde_json::from_value(body)?;

    Ok((fqdn, v))
}
