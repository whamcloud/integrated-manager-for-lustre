// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures_util::stream::TryStreamExt;
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db, get_pool_limit};
use iml_postgres::{get_db_pool, sqlx};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::snapshot;
use influx_db_client::Client;
use std::collections::HashMap;
use thiserror::Error;
use tokio::time;
use url::Url;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[derive(Error, Debug)]
pub enum ImlSnapshotError {
    #[error(transparent)]
    InfluxDbClientError(#[from] influx_db_client::Error),
}

async fn get_stats_from_influx(fs_name: &str, client: &Client) -> Result<(), ImlSnapshotError> {
    let nodes = client
        .query(
            format!(
                r#"
        SELECT 
            SUM(bytes_total) as bytes_total, 
            SUM(bytes_free) as bytes_free, 
            SUM("bytes_avail") as bytes_avail 
            FROM (
                SELECT LAST("bytes_total") AS bytes_total, 
                    LAST("bytes_free") as bytes_free, 
                    LAST("bytes_avail") as bytes_avail 
                FROM "target" 
                WHERE "kind" = 'OST' AND "fs" = '{}' 
                GROUP BY target
            )
    "#,
                fs_name
            )
            .as_str(),
            None,
        )
        .await?;

    tracing::debug!("stats: {:?}", nodes);

    // Some(
    //     [
    //         Node {
    //             statement_id: Some(0),
    //             series: Some(
    //                 [
    //                     Series {
    //                         name: "target",
    //                         tags: None,
    //                         columns: ["time", "bytes_total", "bytes_free", "bytes_avail"],
    //                         values: [
    //                             [String("1970-01-01T00:00:00Z"), Number(20510146560), Number(17197694976), Number(17189306368)]
    //                         ]
    //                     }
    //                 ]
    //             )
    //         }
    //     ]
    // )

    if let Some(nodes) = nodes {
        let items: Vec<HashMap<String, u64>> = nodes
            .into_iter()
            .map(|x| {
                if let Some(series) = x.series {
                    let xs: Vec<HashMap<String, u64>> = series
                        .into_iter()
                        .map(|s| {
                            s.columns
                                .iter()
                                .skip(1)
                                .map(|x| x.to_string())
                                .zip(s.values[0].iter().skip(1).map(|x| x.as_u64().unwrap()))
                                .collect::<HashMap<String, u64>>()
                        })
                        .collect();

                    xs
                } else {
                    vec![]
                }
            })
            .flatten()
            .collect();

        // let bytes_total = series[0].values[0].1;
        // let bytes_free = series[0].values[0].2;
        // let bytes_avail = series[0].values[0].3;
        // let bytes_used = bytes_total - bytes_free;

        // model.metric_data = Some(FsUsage {
        //     bytes_used,
        //     bytes_avail,
        //     bytes_total,
        // });

        // model.percent_used = bytes_used / bytes_total;
    }

    Ok(())
}

async fn handle_retention_rules(pool: sqlx::PgPool) {
    let influx_url: String = format!("http://{}", get_influxdb_addr());
    let influx_client = Client::new(
        Url::parse(&influx_url).expect("Influx URL is invalid."),
        get_influxdb_metrics_db(),
    );

    loop {
        // Get the filesystems that have retention assigned to them.
        let fs_names: Vec<String> = sqlx::query!(
            r#"
                SELECT DISTINCT filesystem_name
                FROM snapshot_retention
            "#
        )
        .fetch_all(&pool)
        .await
        .expect("get filesystems with assigned retention")
        .iter()
        .map(|x| x.filesystem_name.to_string())
        .collect();

        tracing::debug!("Filesystems with retentions: {:?}", fs_names);

        get_stats_from_influx("zfsmo2", &influx_client).await;

        // TODO change this to 60 seconds. 10 is for debugging.
        time::delay_for(time::Duration::from_secs(10)).await;
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<Vec<snapshot::Snapshot>>(&ch, "rust_agent_snapshot_rx");

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;
    sqlx::migrate!("../../migrations").run(&pool).await?;

    tokio::spawn(handle_retention_rules(pool.clone()));

    while let Some((fqdn, snapshots)) = s.try_next().await? {
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

        sqlx::query!(
            r#"
            DELETE FROM snapshot
            WHERE (filesystem_name, snapshot_name) NOT IN (SELECT * FROM UNNEST ($1::text[], $2::text[]))
            "#,
            &snaps.0,
            &snaps.1,
        )
        .execute(&pool)
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
            &snaps.5 as &[Option<bool>],
            &snaps.6 as &[Option<String>],
        )
        .execute(&pool)
        .await?;
    }

    Ok(())
}
