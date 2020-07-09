// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
};
use futures::{lock::Mutex, Future, FutureExt, Stream, TryStreamExt};
use iml_wire_types::{JournalMessage, JournalPriority};
use std::{io, pin::Pin, str, sync::Arc};
use tokio::io::stream_reader;
use tokio_util::codec::{FramedRead, LinesCodec};

#[derive(Debug, PartialEq, serde::Deserialize)]
#[serde(untagged)]
enum Msg {
    String(String),
    Bytes(Vec<u8>),
}

#[derive(Debug, PartialEq, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct IncomingMessage {
    #[serde(rename = "__CURSOR")]
    pub cursor: String,
    #[serde(rename = "__REALTIME_TIMESTAMP")]
    pub realtime_timestamp: String,
    #[serde(rename = "PRIORITY")]
    pub priority: Option<JournalPriority>,
    #[serde(rename = "SYSLOG_FACILITY")]
    pub syslog_facility: Option<String>,
    #[serde(rename = "SYSLOG_IDENTIFIER")]
    pub syslog_identifier: Option<String>,
    #[serde(rename = "MESSAGE")]
    pub message: Msg,
}

#[derive(Debug)]
pub struct Journal {
    cursor: Arc<Mutex<Option<String>>>,
}

pub fn create() -> impl DaemonPlugin {
    Journal {
        cursor: Arc::new(Mutex::new(None)),
    }
}

async fn read_entries(
    cursor: &Option<String>,
) -> Result<impl Stream<Item = Result<(String, JournalMessage), ImlAgentError>>, ImlAgentError> {
    let client = reqwest::Client::new();

    let range = if let Some(x) = cursor {
        format!("entries={}:1:1000", x)
    } else {
        "entries=:-1000:".into()
    };

    let s = client
        .get("http://localhost:19531/entries")
        .header(reqwest::header::RANGE, range)
        .header(reqwest::header::ACCEPT, "application/json")
        .send()
        .await?
        .bytes_stream()
        .map_err(|e| io::Error::new(io::ErrorKind::Other, e));

    let s = stream_reader(s);

    let s = FramedRead::new(s, LinesCodec::new())
        .map_err(ImlAgentError::from)
        .and_then(|x| async move {
            let x: IncomingMessage = serde_json::from_str(&x)?;

            Ok(x)
        })
        .and_then(|x| async move {
            let message = match x.message {
                Msg::String(x) => x,
                Msg::Bytes(x) => std::str::from_utf8(&x)?.to_string(),
            };

            Ok((
                x.cursor,
                JournalMessage {
                    datetime: std::time::Duration::from_micros(
                        x.realtime_timestamp.parse::<u64>()?,
                    ),
                    severity: x.priority.unwrap_or(JournalPriority::Info),
                    facility: x
                        .syslog_facility
                        .unwrap_or_else(|| "3".to_string())
                        .parse::<i16>()?,
                    source: x.syslog_identifier.unwrap_or_else(|| "unknown".to_string()),
                    message,
                },
            ))
        });

    Ok(s)
}

impl DaemonPlugin for Journal {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        self.update_session()
    }
    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        let cursor_lock = Arc::clone(&self.cursor);

        async move {
            let cursor = cursor_lock.lock().await;

            let xs: Vec<_> = read_entries(&cursor).await?.try_collect().await?;
            let (cursors, messages): (Vec<String>, Vec<JournalMessage>) = xs.into_iter().unzip();

            if messages.is_empty() {
                return Ok(None);
            }

            if let Some(new_cursor) = cursors.last() {
                let mut cursor = cursor_lock.lock().await;

                cursor.replace(new_cursor.clone());
            }

            let out = serde_json::to_value(&messages)?;

            Ok(Some(out))
        }
        .boxed()
    }
}
