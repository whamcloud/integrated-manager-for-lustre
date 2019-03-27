// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::prelude::*;
use iml_rabbit::{
    basic_consume, basic_publish, connect_to_queue, create_channel, declare_queue, TcpChannel,
    TcpClient, TcpStreamConsumerFuture,
};
use iml_wire_types::{Fqdn, Id, ManagerMessage, Message, PluginMessage, PluginName, Seq};
use lapin_futures::channel::BasicConsumeOptions;

pub struct AgentData {
    pub fqdn: Fqdn,
    pub plugin: PluginName,
    pub session_id: Id,
    pub session_seq: Seq,
    pub body: serde_json::Value,
}

impl std::fmt::Display for AgentData {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "{:?}/{:?}/{:?}-{:?}",
            self.fqdn, self.plugin, self.session_id, self.session_seq,
        )
    }
}

/// Converts agent Message out of it's enum and into a discrete AgentData
/// struct. This function will panic if the Message is not Data.
impl From<Message> for AgentData {
    fn from(msg: Message) -> Self {
        match msg {
            Message::Data {
                fqdn,
                plugin,
                session_id,
                session_seq,
                body,
                ..
            } => AgentData {
                fqdn,
                plugin,
                session_id,
                session_seq,
                body,
            },
            _ => panic!("Cannot convert to AgentData, Message was not Data"),
        }
    }
}

impl From<AgentData> for PluginMessage {
    fn from(
        AgentData {
            fqdn,
            plugin,
            session_id,
            session_seq,
            body,
        }: AgentData,
    ) -> Self {
        PluginMessage::Data {
            fqdn,
            plugin,
            session_id,
            session_seq,
            body,
        }
    }
}

fn send_message_to_queue<'a, T: 'a + Into<Vec<u8>> + std::fmt::Debug>(
    queue_name: String,
    client: TcpClient,
    msg: T,
) -> impl Future<Item = TcpChannel, Error = failure::Error> + 'a {
    connect_to_queue(queue_name, client.clone())
        .and_then(move |(c, q)| basic_publish("", &q.name(), c, msg))
}

pub fn send_agent_message<'a>(
    client: TcpClient,
    msg: ManagerMessage,
) -> impl Future<Item = TcpClient, Error = failure::Error> + 'a {
    send_message_to_queue("agent_tx_rust".to_string(), client.clone(), msg).map(move |_| client)
}

pub fn send_plugin_message(
    queue_name: String,
    client: TcpClient,
    msg: PluginMessage,
) -> impl Future<Item = TcpClient, Error = failure::Error> + 'static {
    send_message_to_queue(queue_name, client.clone(), msg).map(move |_| client)
}

pub fn terminate_agent_session(
    plugin: &PluginName,
    fqdn: &Fqdn,
    session_id: Id,
    client: TcpClient,
) -> impl Future<Item = TcpClient, Error = failure::Error> {
    send_agent_message(
        client,
        ManagerMessage::SessionTerminate {
            fqdn: fqdn.clone(),
            plugin: plugin.clone(),
            session_id,
        },
    )
}

pub fn consume_agent_tx_queue() -> impl TcpStreamConsumerFuture {
    iml_rabbit::connect_to_rabbit()
        .and_then(create_channel)
        .and_then(|ch| declare_queue("agent_tx_rust".to_string(), ch))
        .and_then(|(ch, q)| {
            basic_consume(
                ch,
                q,
                "agent_tx_rust",
                Some(BasicConsumeOptions {
                    no_ack: true,
                    exclusive: true,
                    ..Default::default()
                }),
            )
        })
}
