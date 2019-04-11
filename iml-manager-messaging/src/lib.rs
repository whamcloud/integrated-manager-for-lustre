// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::prelude::*;
use iml_rabbit::{basic_publish, connect_to_queue, TcpChannelFuture, TcpClient};
use iml_wire_types::{ManagerMessage, PluginMessage, ToBytes};

pub static AGENT_TX_RUST: &'static str = "agent_tx_rust";

fn send_message_to_queue<T: ToBytes + std::fmt::Debug>(
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    client: TcpClient,
    msg: T,
) -> impl TcpChannelFuture {
    connect_to_queue(queue_name, client.clone())
        .and_then(move |(c, q)| basic_publish(c, exchange_name, q.name(), msg))
}

/// Sends an *outgoing* message to an IML agent.
///
/// # Arguments
///
/// * `client` - The active `TcpClient` to connect over.
/// * `queue_name` - The queue to send to.
/// * `msg` - The `ManagerMessage` to send to the agent.
pub fn send_agent_message(
    client: TcpClient,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    msg: ManagerMessage,
) -> impl Future<Item = TcpClient, Error = failure::Error> {
    send_message_to_queue(exchange_name, queue_name, client.clone(), msg).map(move |_| client)
}

/// Sends an *internal* message to a IML manager plugin's queue.
/// Can be used for plugn  -> plugin messaging on the manager side.
///
/// # Arguments
///
/// * `client` - The active `TcpClient` to connect over.
/// * `queue_name` - The name of the queue to connect and send messages over.
/// * `exchange_name` - The name of the exchange to connect to
/// * `msg` - The `PluginMessage` to send to the manager plugin.
pub fn send_plugin_message(
    client: TcpClient,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    msg: PluginMessage,
) -> impl Future<Item = TcpClient, Error = failure::Error> {
    send_message_to_queue(exchange_name, queue_name, client.clone(), msg).map(move |_| client)
}

pub struct RoutingKey<'a>(&'a str);

impl<'a> From<RoutingKey<'a>> for &'a str {
    fn from(key: RoutingKey<'a>) -> Self {
        key.0
    }
}
