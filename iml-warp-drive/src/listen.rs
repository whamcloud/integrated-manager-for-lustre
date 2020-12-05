// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{cache, db_record, error, users, DbRecord};
use futures::{Stream, TryStreamExt};
use iml_wire_types::{
    db::TableName,
    warp_drive::{Message, RecordChange},
};
use std::{convert::TryFrom, sync::Arc};

#[derive(serde::Deserialize, Debug)]
#[serde(rename_all = "UPPERCASE")]
pub enum MessageType {
    Update,
    Insert,
    Delete,
}

fn into_db_record(s: &str) -> serde_json::error::Result<(MessageType, DbRecord)> {
    let (msg_type, table_name, x): (MessageType, TableName, serde_json::Value) =
        serde_json::from_str(&s)?;

    let r = db_record::DbRecord::try_from((table_name, x))?;

    Ok((msg_type, r))
}

async fn handle_record_change(
    record_change: RecordChange,
    api_cache_state: cache::SharedCache,
    user_state: users::SharedUsers,
) {
    match record_change.clone() {
        RecordChange::Delete(r) => {
            tracing::debug!("LISTEN / NOTIFY Delete record: {:?}", r);

            let removed = api_cache_state.lock().await.remove_record(r).is_some();

            if removed {
                users::send_message(
                    Message::RecordChange(record_change),
                    Arc::clone(&user_state),
                )
                .await;
            }
        }
        RecordChange::Update(r) => {
            let record_id = (&r).into();

            let mut cache_state = api_cache_state.lock().await;

            let old_record = cache_state.remove_record(record_id);

            let changed = old_record.as_ref() != Some(&r);

            tracing::debug!(
                ?old_record,
                new_record = ?r,
                changed,
                "LISTEN / NOTIFY Update");

            cache_state.insert_record(r);

            if changed {
                users::send_message(
                    Message::RecordChange(record_change),
                    Arc::clone(&user_state),
                )
                .await;
            }
        }
    };
}

pub async fn handle_db_notifications(
    mut stream: impl Stream<Item = Result<iml_postgres::AsyncMessage, iml_postgres::Error>>
        + std::marker::Unpin,
    client: iml_postgres::SharedClient,
    api_client: iml_manager_client::Client,
    api_cache_state: cache::SharedCache,
    user_state: users::SharedUsers,
) -> Result<(), error::ImlWarpDriveError> {
    // Keep the client alive within the spawned future so the LISTEN/NOTIFY stream is not dropped
    let _keep_alive = &client;

    while let Some(msg) = stream.try_next().await? {
        let api_cache_state = Arc::clone(&api_cache_state);
        let user_state = Arc::clone(&user_state);

        match msg {
            iml_postgres::AsyncMessage::Notification(n) => {
                if n.channel() == "table_update" {
                    let r = into_db_record(n.payload())?;

                    let record_change =
                        cache::db_record_to_change_record(r, api_client.clone()).await?;

                    handle_record_change(record_change, api_cache_state, user_state).await;
                } else {
                    tracing::warn!("unknown channel: {}", n.channel());
                }

                Ok(())
            }
            iml_postgres::AsyncMessage::Notice(err) => {
                tracing::error!("Error from postgres {}", err);

                Err(error::ImlWarpDriveError::from(err))
            }
            _ => unreachable!(),
        }?;
    }

    Ok(())
}
