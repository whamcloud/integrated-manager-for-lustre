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
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

pub async fn get_host_by_fqdn(
    x: &str,
    pool: &iml_orm::DbPool,
) -> Result<Option<ChromaCoreManagedhost>, tokio_diesel::AsyncError> {
    ChromaCoreManagedhost::by_fqdn(x)
        .first_async(pool)
        .await
        .optional()
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let pool = iml_orm::pool()?;

    let mut s = consume_data::<State>("rust_agent_ntp_rx");

    while let Some((fqdn, state)) = s.try_next().await? {
        tracing::debug!("fqdn: {:?} state: {:?}", fqdn, state);

        match state {
            State::Synced => {
                let host = get_host_by_fqdn(&fqdn.0, &pool).await?;

                if let Some(host) = host {
                    alerts::lower(
                        vec![
                            AlertRecordType::TimeOutOfSyncAlert,
                            AlertRecordType::NoTimeSyncAlert,
                            AlertRecordType::MultipleTimeSyncAlert,
                        ],
                        host.id,
                        &pool,
                    )
                    .await?;
                }
            }
            State::None => {
                let host = get_host_by_fqdn(&fqdn.0, &pool).await?;

                if let Some(host) = host {
                    alerts::lower(
                        vec![
                            AlertRecordType::TimeOutOfSyncAlert,
                            AlertRecordType::MultipleTimeSyncAlert,
                        ],
                        host.id,
                        &pool,
                    )
                    .await?;

                    if host.is_setup() {
                        alerts::raise(
                            alerts::AlertRecordType::NoTimeSyncAlert,
                            &format!("No running time sync clients found on {}", fqdn),
                            host.content_type_id.expect("Host has no content_type_id"),
                            host.id,
                            &pool,
                        )
                        .await?;
                    }
                }
            }
            State::Multiple => {
                let host = get_host_by_fqdn(&fqdn.0, &pool).await?;

                if let Some(host) = host {
                    alerts::lower(
                        vec![
                            AlertRecordType::TimeOutOfSyncAlert,
                            AlertRecordType::NoTimeSyncAlert,
                        ],
                        host.id,
                        &pool,
                    )
                    .await?;

                    if host.is_setup() {
                        alerts::raise(
                            alerts::AlertRecordType::MultipleTimeSyncAlert,
                            &format!("Multiple running time sync clients found on {}", fqdn),
                            host.content_type_id.expect("Host has no content_type_id"),
                            host.id,
                            &pool,
                        )
                        .await?;
                    }
                }
            }
            State::Unsynced(_) => {
                let host = get_host_by_fqdn(&fqdn.0, &pool).await?;

                if let Some(host) = host {
                    alerts::lower(
                        vec![
                            AlertRecordType::MultipleTimeSyncAlert,
                            AlertRecordType::NoTimeSyncAlert,
                        ],
                        host.id,
                        &pool,
                    )
                    .await?;

                    if host.is_setup() {
                        alerts::raise(
                            alerts::AlertRecordType::TimeOutOfSyncAlert,
                            &format!("Time is out of sync on server {}", fqdn),
                            host.content_type_id.expect("Host has no content_type_id"),
                            host.id,
                            &pool,
                        )
                        .await?;
                    }
                }
            }
        };
    }

    Ok(())
}
