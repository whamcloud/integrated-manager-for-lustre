// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_agent::{
    agent_error::EmfAgentError, env, env::get_journal_port, util::create_filtered_writer,
};
use emf_wire_types::{JournalMessage, JournalPriority};
use lazy_static::lazy_static;
use std::{convert::TryFrom, str, time::Duration};
use tokio::time::interval;

#[derive(Debug, PartialEq, serde::Deserialize)]
#[serde(untagged)]
enum Msg {
    String(String),
    Bytes(Vec<u8>),
}

lazy_static! {
    static ref URL: String = format!("http://localhost:{}/entries", get_journal_port());
}

#[derive(Debug, PartialEq, serde::Deserialize)]
struct IncomingMessage {
    #[serde(rename = "__CURSOR")]
    pub cursor: String,
    #[serde(rename = "__REALTIME_TIMESTAMP")]
    pub realtime_timestamp: String,
    #[serde(rename = "PRIORITY")]
    pub priority: Option<String>,
    #[serde(rename = "SYSLOG_FACILITY")]
    pub syslog_facility: Option<String>,
    #[serde(rename = "SYSLOG_IDENTIFIER")]
    pub syslog_identifier: Option<String>,
    #[serde(rename = "MESSAGE")]
    pub message: Msg,
}

async fn read_entries(
    cursor: Option<&str>,
) -> Result<Vec<(String, JournalMessage)>, EmfAgentError> {
    let client = reqwest::Client::new();

    let range = if let Some(x) = cursor {
        format!("entries={}:1:1000", x)
    } else {
        "entries=:-999:".into()
    };

    tracing::debug!("Journal Range header: {}", range);

    let xs = client
        .get(URL.as_str())
        .header(reqwest::header::RANGE, range)
        .header(reqwest::header::ACCEPT, "application/json")
        .send()
        .await?
        .text()
        .await?
        .lines()
        .map(|x| serde_json::from_str(&x))
        .collect::<Result<Vec<IncomingMessage>, _>>()?;

    let xs = xs
        .into_iter()
        .map(|x| {
            let message = match x.message {
                Msg::String(x) => x,
                Msg::Bytes(x) => std::str::from_utf8(&x)?.to_string(),
            };

            let priority = match x.priority {
                Some(x) => JournalPriority::try_from(x)?,
                None => JournalPriority::Info,
            };

            let journal_message = JournalMessage {
                datetime: std::time::Duration::from_micros(x.realtime_timestamp.parse::<u64>()?),
                severity: priority,
                facility: x
                    .syslog_facility
                    .unwrap_or_else(|| "3".to_string())
                    .parse::<i16>()?,
                source: x.syslog_identifier.unwrap_or_else(|| "unknown".to_string()),
                message,
            };

            Ok((x.cursor, journal_message))
        })
        .collect::<Result<Vec<_>, EmfAgentError>>()?;

    Ok(xs)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let mut x = interval(Duration::from_secs(5));

    let mut cursor: Option<String> = None;

    let port = env::get_port("JOURNAL_AGENT_JOURNAL_SERVICE_PORT");
    let writer = create_filtered_writer(port);

    loop {
        x.tick().await;

        let xs = read_entries(cursor.as_deref()).await?;
        let (cursors, messages): (Vec<String>, Vec<JournalMessage>) = xs.into_iter().unzip();

        if messages.is_empty() {
            tracing::debug!("No new journal messages since last tick");

            continue;
        }

        if let Some(new_cursor) = cursors.last() {
            tracing::debug!("Replacing cursor with {}", new_cursor);

            cursor.replace(new_cursor.clone());
        }

        let _ = writer.send(messages);
    }
}
