// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_influx::Client as InfluxClient;
use emf_manager_client::{Client as ManagerClient, Url};
use emf_manager_env::{get_influxdb_metrics_db, get_pool_limit};
use emf_postgres::get_db_pool;
use emf_service_queue::spawn_service_consumer;
use emf_snapshot::{client_monitor::tick, retention::handle_retention_rules, MonitorState};
use emf_tracing::tracing;
use emf_wire_types::snapshot;
use futures::StreamExt;
use std::collections::HashMap;
use tokio::time::{interval, Duration};

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let mut rx = spawn_service_consumer::<HashMap<String, Vec<snapshot::Snapshot>>>(
        emf_manager_env::get_port("SNAPSHOT_SERVICE_PORT"),
    );

    let pool = get_db_pool(
        get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT),
        emf_manager_env::get_port("SNAPSHOT_SERVICE_PG_PORT"),
    )
    .await?;
    let pool_2 = pool.clone();
    let pool_3 = pool.clone();

    sqlx::migrate!("../../migrations").run(&pool).await?;

    let manager_client: ManagerClient = emf_manager_client::get_client()?;

    let influx_url: String = format!(
        "http://127.0.0.1:{}",
        emf_manager_env::get_port("SNAPSHOT_SERVICE_INFLUX_PORT")
    );
    let influx_client = InfluxClient::new(
        Url::parse(&influx_url).expect("Influx URL is invalid."),
        get_influxdb_metrics_db(),
    );

    tokio::spawn(async move {
        let mut interval = interval(Duration::from_secs(60));
        let mut snapshot_client_counts: HashMap<i32, MonitorState> = HashMap::new();

        loop {
            interval.tick().await;

            let tick_result = tick(&mut snapshot_client_counts, pool_2.clone()).await;
            if let Err(e) = tick_result {
                tracing::error!("Error during handling snapshot autounmount: {}", e);
            }
        }
    });

    tokio::spawn(handle_retention_rules(
        manager_client,
        influx_client,
        pool_3.clone(),
    ));

    while let Some((fqdn, snap_map)) = rx.next().await {
        for (fs_name, snapshots) in snap_map {
            tracing::debug!("snapshots from {}: {:?}", fqdn, snapshots);

            let snaps = snapshots.into_iter().fold(
                (vec![], vec![], vec![], vec![], vec![], vec![], vec![]),
                |mut acc, s| {
                    acc.0.push(s.filesystem_name);
                    acc.1.push(s.snapshot_name);
                    acc.2.push(s.create_time.naive_utc());
                    acc.3.push(s.modify_time.naive_utc());
                    acc.4.push(s.snapshot_fsname.clone());
                    acc.5.push(s.mounted);
                    acc.6.push(s.comment);

                    acc
                },
            );

            let mut transaction = pool.begin().await?;

            sqlx::query!(
                r#"
                DELETE FROM snapshot
                WHERE snapshot_name NOT IN (SELECT * FROM UNNEST ($1::text[]))
                AND filesystem_name=$2::text
                "#,
                &snaps.1,
                &fs_name,
            )
            .execute(&mut transaction)
            .await?;

            sqlx::query!(
            r#"
            INSERT INTO snapshot (filesystem_name, snapshot_name, create_time, modify_time, snapshot_fsname, mounted, comment)
            SELECT * FROM
            UNNEST (
                $1::text[],
                $2::text[],
                $3::timestamp[],
                $4::timestamp[],
                $5::text[],
                $6::bool[],
                $7::text[]
            )
            ON CONFLICT (filesystem_name, snapshot_name) DO UPDATE
            SET
                create_time = excluded.create_time,
                modify_time = excluded.modify_time,
                snapshot_fsname = excluded.snapshot_fsname,
                mounted = excluded.mounted,
                comment = excluded.comment
            "#,
            &snaps.0,
            &snaps.1,
            &snaps.2,
            &snaps.3,
            &snaps.4,
            &snaps.5,
            &snaps.6 as &[Option<String>],
        )
        .execute(&mut transaction)
        .await?;

            transaction.commit().await?;
        }
    }

    Ok(())
}
