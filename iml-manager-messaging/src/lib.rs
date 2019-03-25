// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::future::{self, Either};
use futures::prelude::*;
use iml_rabbit::{basic_publish, connect_to_queue, create_channel, TcpChannelFuture, TcpClient};
use iml_wire_types::{ManagerMessage, PluginMessage};

fn send_message_to_queue<'a, T: 'a + Into<Vec<u8>> + std::fmt::Debug>(
    queue_name: String,
    client: TcpClient,
    msg: T,
) -> impl TcpChannelFuture + 'a {
    connect_to_queue(queue_name, client.clone())
        .and_then(move |(c, q)| basic_publish("", &q.name(), c, msg))
}

/// Sends an *outgoing* message to an IML agent.
///
/// # Arguments
///
/// * `client` - The active `TcpClient` to connect over.
/// * `msg` - The `ManagerMessage` to send to the agent.
pub fn send_agent_message<'a>(
    client: TcpClient,
    msg: ManagerMessage,
) -> impl Future<Item = TcpClient, Error = failure::Error> + 'a {
    send_message_to_queue("agent_tx_rust".to_string(), client.clone(), msg).map(move |_| client)
}

/// Sends an *internal* message to a IML manager plugin's queue.
/// Can be used for plugn  -> plugin messaging on the manager side.
///
/// # Arguments
///
/// * `client` - The active `TcpClient` to connect over.
/// * `queue_name` - The name of the queue to connect and send messages over.
/// * `msg` - The `PluginMessage` to send to the manager plugin.
pub fn send_plugin_message(
    client: TcpClient,
    queue_name: String,
    msg: PluginMessage,
) -> impl Future<Item = TcpClient, Error = failure::Error> + 'static {
    send_message_to_queue(queue_name, client.clone(), msg).map(move |_| client)
}

pub struct RoutingKey<'a>(&'a str);

impl<'a> From<&RoutingKey<'a>> for &'a str {
    fn from(key: &RoutingKey<'a>) -> Self {
        key.0
    }
}

/// Sends an *internal* message using the [Direct reply-to](https://www.rabbitmq.com/direct-reply-to.html)
/// feature of RabbitMQ.
///
/// # Arguments
///
/// * `client` - The active `TcpClient` to connect over.
/// * `routing_key` - The routing key to reply to.
/// * `msg` - The `PluginMessage` to send to the manager plugin.
pub fn send_direct_reply(
    client: TcpClient,
    routing_key: &'static RoutingKey<'_>,
    msg: impl serde::Serialize,
) -> impl TcpChannelFuture + 'static {
    match serde_json::to_vec(&msg) {
        Ok(v) => Either::A(
            create_channel(client).and_then(move |ch| basic_publish("", routing_key.into(), ch, v)),
        ),
        Err(e) => Either::B(future::err(e.into())),
    }
}
