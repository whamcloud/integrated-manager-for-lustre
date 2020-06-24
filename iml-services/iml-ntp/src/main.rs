// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryStreamExt;
use iml_orm::{
    alerts::{self, AlertRecordType},
    hosts::ChromaCoreManagedhost,
    tokio_diesel::{self, AsyncRunQueryDsl as _, OptionalExtension as _},
};
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::time::State;

pub async fn get_host_by_fqdn(
    x: impl ToString,
    pool: &iml_orm::DbPool,
) -> Result<Option<ChromaCoreManagedhost>, tokio_diesel::AsyncError> {
    ChromaCoreManagedhost::by_fqdn(x)
        .first_async(pool)
        .await
        .optional()
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let pool = iml_orm::pool()?;

    let rabbit_pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(rabbit_pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<State>(&ch, "rust_agent_ntp_rx");

    while let Some((fqdn, state)) = s.try_next().await? {
        tracing::debug!("fqdn: {:?} state: {:?}", fqdn, state);

        let host = get_host_by_fqdn(&fqdn.0, &pool).await?;

        let host = match host {
            Some(host) => host,
            None => continue,
        };

        match state {
            State::Synced => {
                alerts::lower(
                    vec![
                        AlertRecordType::TimeOutOfSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .execute_async(&pool)
                .await?;
            }
            State::None => {
                alerts::lower(
                    vec![
                        AlertRecordType::TimeOutOfSyncAlert,
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .execute_async(&pool)
                .await?;

                if host.is_setup() {
                    alerts::raise(
                        AlertRecordType::NoTimeSyncAlert,
                        format!("No running time sync clients found on {}", fqdn),
                        host.content_type_id.expect("Host has no content_type_id"),
                        host.id,
                    )
                    .execute_async(&pool)
                    .await?;
                }
            }
            State::Multiple => {
                alerts::lower(
                    vec![
                        AlertRecordType::TimeOutOfSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .execute_async(&pool)
                .await?;

                if host.is_setup() {
                    alerts::raise(
                        AlertRecordType::MultipleTimeSyncAlert,
                        format!("Multiple running time sync clients found on {}", fqdn),
                        host.content_type_id.expect("Host has no content_type_id"),
                        host.id,
                    )
                    .execute_async(&pool)
                    .await?;
                }
            }
            State::Unsynced(_) => {
                alerts::lower(
                    vec![
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .execute_async(&pool)
                .await?;

                if host.is_setup() {
                    alerts::raise(
                        AlertRecordType::TimeOutOfSyncAlert,
                        format!("Time is out of sync on server {}", fqdn),
                        host.content_type_id.expect("Host has no content_type_id"),
                        host.id,
                    )
                    .execute_async(&pool)
                    .await?;
                }
            }
            State::Unknown => {
                alerts::lower(
                    vec![
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::TimeOutOfSyncAlert,
                    ],
                    host.id,
                )
                .execute_async(&pool)
                .await?;

                if host.is_setup() {
                    alerts::raise(
                        AlertRecordType::UnknownTimeSyncAlert,
                        format!("Unable to determine time sync status on {}", fqdn),
                        host.content_type_id.expect("Host has no content_type_id"),
                        host.id,
                    )
                    .execute_async(&pool)
                    .await?;
                }
            }
        };
    }

    Ok(())
}
