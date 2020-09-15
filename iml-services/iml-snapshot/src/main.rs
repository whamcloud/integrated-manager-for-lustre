// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use core::fmt::Debug;
use futures_util::stream::TryStreamExt;
use iml_api_utils::wait_for_cmds_success;
use iml_graphql_queries::snapshot as snapshot_queries;
use iml_manager_client::{get_influx, graphql};
use iml_manager_env::get_pool_limit;
use iml_postgres::{get_db_pool, sqlx};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::snapshot;
use reqwest::Client;
use std::{collections::HashMap, sync::Arc};
use tokio::{
    sync::Mutex,
    time::Instant,
    time::{interval, Duration},
};

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[derive(Debug, PartialEq, Eq, Hash, Clone)]
struct SnapshotId {
    filesystem_name: String,
    snapshot_name: String,
    snapshot_fsname: String,
}

#[derive(Debug, PartialEq, Eq, Hash, Clone)]
enum State {
    Monitoring(u64),
    CountingDown(Instant),
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

    let snapshot_client_counts: Arc<Mutex<HashMap<SnapshotId, Option<State>>>> =
        Arc::new(Mutex::new(HashMap::new()));
    let snapshot_client_counts_2 = snapshot_client_counts.clone();

    tokio::spawn(async move {
        let mut interval = interval(Duration::from_secs(10));

        use tokio::stream::StreamExt;
        while let Some(_) = interval.next().await {
            let client: Client = iml_manager_client::get_client().unwrap();
            let client_2 = client.clone();

            let query = iml_influx::filesystems::query();
            let stats_fut = get_influx::<iml_influx::filesystems::InfluxResponse>(
                client,
                "iml_stats",
                query.as_str(),
            );

            let influx_resp = stats_fut.await.unwrap();
            let stats = iml_influx::filesystems::Response::from(influx_resp);

            tracing::debug!("ST: {:?}", stats);
            let mut snapshot_client_counts = snapshot_client_counts_2.lock().await;

            for (snapshot_id, state) in snapshot_client_counts.iter_mut() {
                if let Some(snapshot_stats) = stats.get(&snapshot_id.snapshot_fsname) {
                    match state {
                        Some(State::Monitoring(prev_clients)) => {
                            let clients = snapshot_stats.clients.unwrap_or(0);

                            tracing::info!(
                                "Monitoring. Snapshot: {}, was {} clients, became {} clients",
                                &snapshot_id.snapshot_fsname,
                                prev_clients,
                                clients
                            );
                            if *prev_clients > 0 && clients == 0 {
                                tracing::info!("counting down for job");
                                // let instant = Instant::now() + Duration::from_secs(5 * 60);
                                let instant = Instant::now() + Duration::from_secs(20);
                                *state = Some(State::CountingDown(instant));
                            } else {
                                *prev_clients = clients;
                            }
                        }
                        Some(State::CountingDown(when)) => {
                            let clients = snapshot_stats.clients.unwrap_or(0);
                            tracing::info!(
                                "Counting down. Snapshot: {}, Was 0 clients, became {} clients",
                                &snapshot_id.snapshot_fsname,
                                clients
                            );
                            if clients > 0 {
                                tracing::info!("changing state");
                                *state = Some(State::Monitoring(clients));
                            } else if Instant::now() >= *when {
                                tracing::info!("running the job");
                                *state = Some(State::Monitoring(0));

                                let query = snapshot_queries::unmount::build(
                                    &snapshot_id.filesystem_name,
                                    &snapshot_id.snapshot_name,
                                );
                                let resp: iml_graphql_queries::Response<
                                    snapshot_queries::unmount::Resp,
                                > = graphql(client_2.clone(), query).await.unwrap();
                                let command = Result::from(resp).unwrap().data.unmount_snapshot;
                                wait_for_cmds_success(&[command]).await.unwrap();
                            }
                        }
                        None => {
                            tracing::info!(
                                "Just learnt about this snapshot. Snapshot: {}, became 0 clients",
                                &snapshot_id.snapshot_fsname
                            );

                            *state = Some(State::Monitoring(0));
                        }
                    }
                }
            }
        }
    });

    while let Some((fqdn, snapshots)) = s.try_next().await? {
        tracing::debug!("snapshots from {}: {:?}", fqdn, snapshots);

        let snaps = {
            let mut snapshot_fsnames = snapshot_client_counts.lock().await;

            snapshots.into_iter().fold(
                (vec![], vec![], vec![], vec![], vec![], vec![], vec![]),
                |mut acc, s| {
                    acc.0.push(s.filesystem_name.clone());
                    acc.1.push(s.snapshot_name.clone());
                    acc.2.push(s.create_time.naive_utc());
                    acc.3.push(s.modify_time.naive_utc());
                    acc.4.push(s.snapshot_fsname.clone());
                    acc.5.push(s.mounted);
                    acc.6.push(s.comment);

                    snapshot_fsnames
                        .entry(SnapshotId {
                            filesystem_name: s.filesystem_name,
                            snapshot_name: s.snapshot_name,
                            snapshot_fsname: s.snapshot_fsname,
                        })
                        .or_insert(None);
                    // TODO: handle removal

                    acc
                },
            )
        };

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
