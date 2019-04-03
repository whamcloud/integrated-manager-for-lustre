// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_rabbit::{
    basic_consume, create_channel, declare_transient_exchange, declare_transient_queue,
};
use lapin_futures::channel::BasicConsumeOptions;
use tokio::prelude::*;

#[derive(serde::Deserialize)]
pub struct ManagerCommand {
    fqdn: String,
    action: String,
    args: Vec<String>,
}

pub fn start() -> impl Stream<Item = ManagerCommand, Error = failure::Error> {
    iml_rabbit::connect_to_rabbit()
        .and_then(create_channel)
        .and_then(|ch| declare_transient_exchange(ch, "rust_action_runner", "direct"))
        .and_then(|ch| declare_transient_queue("rust_action_runner".to_string(), ch))
        .and_then(|(ch, q)| {
            basic_consume(
                ch,
                q,
                "",
                Some(BasicConsumeOptions {
                    no_ack: true,
                    exclusive: true,
                    ..Default::default()
                }),
            )
        })
        .map(|s| s.map_err(failure::Error::from))
        .flatten_stream()
        .and_then(|m| {
            log::trace!("Incoming message: {:?}", m.data);
            serde_json::from_slice(&m.data).map_err(failure::Error::from)
        })
}
