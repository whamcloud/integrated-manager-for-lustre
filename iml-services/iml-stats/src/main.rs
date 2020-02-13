// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::stream::TryStreamExt;
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db};
use iml_service_queue::service_queue::consume_data;
use iml_stats::error::ImlStatsError;
use influxdb::{Client, Query, Timestamp};
use lustre_collector::{Record, TargetStats};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), ImlStatsError> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let mut s = consume_data::<Vec<Record>>("rust_agent_stats_rx");

    while let Some((host, xs)) = s.try_next().await? {
        tracing::info!("Incoming stats: {:?}", xs);

        let client = Client::new(get_influxdb_addr().to_string(), get_influxdb_metrics_db());
        //Write the entry into the influxdb database
        for record in xs {
            let maybe_entry = match record {
                Record::Target(target_stats) => match target_stats {
                    TargetStats::FilesFree(x) => {
                        let q = Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("bytes_free", x.value);
                        Some(q)
                    }
                    _ => {
                        tracing::debug!("Received target stat type that is not implemented yet.");

                        None
                    }
                },
                _ => {
                    tracing::debug!("Received record type that is not iplemented yet.");

                    None
                }
            };

            if let Some(entry) = maybe_entry {
                let r = client.query(&entry).await?;

                tracing::debug!("Result of writing series to influxdb: {}", r);
            }
        }
    }

    Ok(())
}
