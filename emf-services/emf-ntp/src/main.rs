// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_manager_env::get_pool_limit;
use emf_postgres::{alert, get_db_pool};
use emf_service_queue::spawn_service_consumer;
use emf_wire_types::{time::State, AlertRecordType, AlertSeverity, ComponentType};
use futures::StreamExt;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pool = get_db_pool(
        get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT),
        emf_manager_env::get_port("NTP_SERVICE_PG_PORT"),
    )
    .await?;

    let mut rx = spawn_service_consumer::<State>(emf_manager_env::get_port("NTP_SERVICE_PORT"));

    while let Some((fqdn, state)) = rx.next().await {
        tracing::debug!("fqdn: {:?} state: {:?}", fqdn, state);

        let host = sqlx::query!("select * from host where fqdn = $1", fqdn.to_string())
            .fetch_optional(&pool)
            .await?;

        let host = match host {
            Some(x) => x,
            None => {
                tracing::warn!("Host '{}' is unknown", fqdn);

                continue;
            }
        };

        match state {
            State::Synced => {
                alert::lower(
                    &pool,
                    vec![
                        AlertRecordType::TimeOutOfSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .await?;
            }
            State::None => {
                alert::lower(
                    &pool,
                    vec![
                        AlertRecordType::TimeOutOfSyncAlert,
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .await?;

                alert::raise(
                    &pool,
                    AlertRecordType::NoTimeSyncAlert,
                    format!("No running time sync clients found on {}", fqdn),
                    ComponentType::Host,
                    None,
                    AlertSeverity::ERROR,
                    host.id,
                )
                .await?;
            }
            State::Multiple => {
                alert::lower(
                    &pool,
                    vec![
                        AlertRecordType::TimeOutOfSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .await?;

                alert::raise(
                    &pool,
                    AlertRecordType::MultipleTimeSyncAlert,
                    format!("Multiple running time sync clients found on {}", fqdn),
                    ComponentType::Host,
                    None,
                    AlertSeverity::ERROR,
                    host.id,
                )
                .await?;
            }
            State::Unsynced(_) => {
                alert::lower(
                    &pool,
                    vec![
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::UnknownTimeSyncAlert,
                    ],
                    host.id,
                )
                .await?;

                alert::raise(
                    &pool,
                    AlertRecordType::TimeOutOfSyncAlert,
                    format!("Time is out of sync on server {}", fqdn),
                    ComponentType::Host,
                    None,
                    AlertSeverity::ERROR,
                    host.id,
                )
                .await?;
            }
            State::Unknown => {
                alert::lower(
                    &pool,
                    vec![
                        AlertRecordType::MultipleTimeSyncAlert,
                        AlertRecordType::NoTimeSyncAlert,
                        AlertRecordType::TimeOutOfSyncAlert,
                    ],
                    host.id,
                )
                .await?;

                alert::raise(
                    &pool,
                    AlertRecordType::UnknownTimeSyncAlert,
                    format!("Unable to determine time sync status on {}", fqdn),
                    ComponentType::Host,
                    None,
                    AlertSeverity::ERROR,
                    host.id,
                )
                .await?;
            }
        };
    }

    Ok(())
}
