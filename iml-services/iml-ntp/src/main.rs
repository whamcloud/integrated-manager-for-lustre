// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::stream::TryStreamExt;
use iml_ntp::db::{
    add_alert, get_active_alert_for_fqdn, get_managed_host_items, set_alert_inactive,
};
use iml_postgres::connect;
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::ntp::{TimeStatus, TimeSync};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

pub fn valid_state(mh_state: String) -> bool {
    ["monitored", "managed", "working"]
        .iter()
        .find(|&&x| x == mh_state)
        .is_some()
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();
    tracing::subscriber::set_global_default(subscriber).unwrap();

    let mut s = consume_data::<TimeStatus>("rust_agent_ntp_rx");

    while let Some((fqdn, time_status)) = s.try_next().await? {
        tracing::debug!("fqdn: {:?} time_status: {:?}", fqdn, time_status);

        let (mut client, conn) = connect().await?;

        tokio::spawn(async move {
            conn.await
                .unwrap_or_else(|e| tracing::error!("DB connection error {}", e));
        });

        let alert_id = get_active_alert_for_fqdn(&fqdn.0, &mut client).await?;

        if let Some(alert_id) = alert_id {
            if time_status.synced == TimeSync::Synced {
                tracing::info!(
                    "Setting alert item {} to inactive for host {}.",
                    alert_id,
                    fqdn.0
                );

                set_alert_inactive(alert_id, &mut client).await?;
            }
        } else if time_status.synced == TimeSync::Unsynced {
            let host_info = get_managed_host_items(&fqdn.0, &mut client).await?;
            tracing::debug!(
                "host info used to create new NtpOutOfSync entry: {:?}",
                host_info
            );

            if let Some((content_type_id, managed_host_id, managed_host_state)) = host_info {
                let is_valid_state = valid_state(managed_host_state);

                tracing::debug!("is valid state: {:?}", is_valid_state);

                if is_valid_state && alert_id.is_none() {
                    tracing::info!("Creating new NtpOutOfSync entry for {}", fqdn.0);
                    add_alert(&fqdn.0, content_type_id, managed_host_id, &mut client).await?;
                }
            }
        }
    }

    Ok(())
}
