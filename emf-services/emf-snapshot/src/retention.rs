use crate::{Error, FsStats};
use emf_command_utils::wait_for_cmds_success;
use emf_influx::{Client as InfluxClient, InfluxClientExt as _};
use emf_manager_client::{graphql, Client};
use emf_postgres::{sqlx, PgPool};
use emf_tracing::tracing;
use emf_wire_types::{snapshot, Command};
use std::collections::HashMap;

async fn get_stats_from_influx(
    fs_name: &str,
    client: &InfluxClient,
) -> Result<Option<(u64, u64, u64)>, Error> {
    let nodes: Option<Vec<FsStats>> = client
        .query_into(
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
                fs_name,
            )
            .as_str(),
            None,
        )
        .await?;

    if let Some(nodes) = nodes {
        if nodes.is_empty() {
            return Ok(None);
        } else {
            let bytes_avail = nodes[0].bytes_avail;
            let bytes_total = nodes[0].bytes_total;
            let bytes_free = nodes[0].bytes_free;
            let bytes_used = bytes_total - bytes_free;

            return Ok(Some((bytes_avail, bytes_free, bytes_used)));
        }
    }

    Ok(None)
}

async fn get_snapshots(
    pool: &sqlx::PgPool,
    fs_name: &str,
) -> Result<Vec<snapshot::SnapshotRecord>, Error> {
    let xs = sqlx::query_as!(
        snapshot::SnapshotRecord,
        "SELECT * FROM snapshot WHERE filesystem_name = $1 ORDER BY create_time ASC",
        fs_name
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

async fn get_retentions(pool: &sqlx::PgPool) -> Result<Vec<snapshot::SnapshotRetention>, Error> {
    let xs = sqlx::query_as!(
        snapshot::SnapshotRetention,
        r#"
                SELECT
                    id,
                    filesystem_name,
                    reserve_value,
                    reserve_unit as "reserve_unit:snapshot::ReserveUnit",
                    last_run,
                    keep_num
                FROM snapshot_retention
            "#
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

async fn get_retention_policy(
    pool: &PgPool,
    fs_name: &str,
) -> Result<Option<snapshot::SnapshotRetention>, Error> {
    let xs = get_retentions(pool).await?;

    Ok(xs.into_iter().find(|x| x.filesystem_name == fs_name))
}

async fn destroy_snapshot(
    client: Client,
    fs_name: &str,
    snapshot_name: &str,
) -> Result<Command, Error> {
    let resp: emf_graphql_queries::Response<emf_graphql_queries::snapshot::destroy::Resp> =
        graphql(
            client,
            emf_graphql_queries::snapshot::destroy::build(fs_name, snapshot_name, true),
        )
        .await?;

    let cmd = Result::from(resp)?.data.destroy_snapshot;

    Ok(cmd)
}

async fn get_retention_filesystems(pool: &PgPool) -> Result<Vec<String>, Error> {
    let xs = get_retentions(pool).await?;

    let fs_names = xs.into_iter().map(|x| x.filesystem_name).collect();
    Ok(fs_names)
}

pub async fn process_retention(
    client: &Client,
    influx_client: &InfluxClient,
    pool: &PgPool,
    mut stats_record: HashMap<String, u64>,
) -> Result<HashMap<String, u64>, Error> {
    let filesystems = get_retention_filesystems(pool).await?;

    tracing::debug!("Filesystems with retentions: {:?}", filesystems);

    for fs_name in filesystems {
        let stats = get_stats_from_influx(&fs_name, &influx_client).await?;

        if let Some((bytes_avail, bytes_free, bytes_used)) = stats {
            tracing::debug!(
                "stats values: {}, {}, {}",
                bytes_avail,
                bytes_free,
                bytes_used
            );
            let percent_used =
                (bytes_used as f64 / (bytes_used as f64 + bytes_avail as f64)) as f64 * 100.0f64;
            let percent_free = 100.0f64 - percent_used;

            tracing::debug!(
                "stats record: {:?} - bytes free: {}",
                stats_record.get(&fs_name),
                bytes_free
            );
            let retention = get_retention_policy(pool, &fs_name).await?;

            if let Some(retention) = retention {
                let snapshots = get_snapshots(pool, &fs_name).await?;

                tracing::debug!(
                    "percent_left: {}, reserve value: {}",
                    percent_free,
                    retention.reserve_value
                );
                let should_delete_snapshot = match retention.reserve_unit {
                    snapshot::ReserveUnit::Percent => percent_free < retention.reserve_value as f64,
                    snapshot::ReserveUnit::Gibibytes => {
                        let gib_free: f64 = bytes_free as f64 / 1_073_741_824_f64;
                        gib_free < retention.reserve_value as f64
                    }
                    snapshot::ReserveUnit::Tebibytes => {
                        let teb_free: f64 = bytes_free as f64 / 1_099_511_627_776_f64;
                        teb_free < retention.reserve_value as f64
                    }
                };
                tracing::debug!("Should delete snapshot?: {}", should_delete_snapshot);

                if should_delete_snapshot
                    && snapshots.len() > retention.keep_num as usize
                    && stats_record.get(&fs_name) != Some(&bytes_used)
                {
                    stats_record.insert(fs_name.to_string(), bytes_used);
                    tracing::debug!("About to delete earliest snapshot.");
                    let snapshot_name = snapshots[0].snapshot_name.to_string();
                    tracing::debug!("Deleting {}", snapshot_name);
                    let cmd =
                        destroy_snapshot(client.clone(), &fs_name, snapshot_name.as_ref()).await?;

                    wait_for_cmds_success(&[cmd], None).await?;
                }
            }
        }
    }

    Ok(stats_record)
}

pub async fn handle_retention_rules(
    client: Client,
    influx_client: InfluxClient,
    pool: PgPool,
) -> Result<(), Error> {
    let mut prev_stats: HashMap<String, u64> = vec![].into_iter().collect::<HashMap<String, u64>>();

    loop {
        prev_stats =
            match process_retention(&client, &influx_client, &pool, prev_stats.clone()).await {
                Ok(x) => x,
                Err(e) => {
                    tracing::error!("Retention Rule processing error: {:?}", e);
                    prev_stats
                }
            };

        tokio::time::delay_for(tokio::time::Duration::from_secs(60)).await;
    }
}
