// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_rabbit::{
    basic_consume, declare_transient_queue, BasicConsumeOptions, Channel, EmfRabbitError,
};
use emf_wire_types::{Fqdn, Id, Message, PluginMessage, PluginName};
use futures::{Stream, TryFutureExt, TryStreamExt};

pub static AGENT_TX_RUST: &str = "agent_tx_rust";

#[derive(Debug, serde::Serialize)]
pub struct AgentData {
    pub fqdn: Fqdn,
    pub plugin: PluginName,
    pub session_id: Id,
    pub session_seq: u64,
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

pub async fn consume_agent_tx_queue(
    channel: &Channel,
    queue_name: impl Into<String>,
) -> Result<impl Stream<Item = Result<emf_rabbit::message::Delivery, EmfRabbitError>>, EmfRabbitError>
{
    let q = declare_transient_queue(&channel, queue_name).await?;

    basic_consume(
        &channel,
        q,
        "",
        Some(BasicConsumeOptions {
            no_ack: true,
            ..BasicConsumeOptions::default()
        }),
    )
    .map_ok(|s| s.map_ok(|(_, y)| y))
    .await
}
