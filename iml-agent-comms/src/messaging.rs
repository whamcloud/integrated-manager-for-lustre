// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{Future, Stream};
use iml_rabbit::{
    basic_consume, declare_transient_queue, BasicConsumeOptions, Channel, Client, ImlRabbitError,
};
use iml_wire_types::{Fqdn, Id, ManagerMessage, Message, PluginMessage, PluginName, Seq};

pub static AGENT_TX_RUST: &str = "agent_tx_rust";

#[derive(Debug, serde::Serialize)]
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

/// Converts agent Message out of it's enum and into a discrete `AgentData`
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
            } => Self {
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

pub fn terminate_agent_session(
    plugin: PluginName,
    fqdn: Fqdn,
    session_id: Id,
    client: Client,
) -> impl Future<Output = Result<(), ImlRabbitError>> {
    iml_rabbit::send_message(
        client,
        "",
        AGENT_TX_RUST,
        ManagerMessage::SessionTerminate {
            fqdn,
            plugin,
            session_id,
        },
    )
}

pub async fn consume_agent_tx_queue(
    channel: Channel,
    queue_name: impl Into<String>,
) -> Result<impl Stream<Item = Result<iml_rabbit::message::Delivery, ImlRabbitError>>, ImlRabbitError>
{
    let (ch, q) = declare_transient_queue(channel, queue_name).await?;

    basic_consume(
        ch,
        q,
        "",
        Some(BasicConsumeOptions {
            no_ack: true,
            exclusive: true,
            ..BasicConsumeOptions::default()
        }),
    )
    .await
}
