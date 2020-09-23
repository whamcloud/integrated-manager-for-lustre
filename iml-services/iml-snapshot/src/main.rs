// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{StreamExt, TryStreamExt};
use iml_command_utils::{wait_for_cmds_success, CmdUtilError};
use iml_graphql_queries::snapshot as snapshot_queries;
use iml_manager_client::{get_influx, graphql, Client, ImlManagerClientError};
use iml_manager_env::get_pool_limit;
use iml_postgres::{get_db_pool, sqlx, PgPool};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::snapshot;
use std::{collections::HashMap, fmt::Debug};
use thiserror::Error;
use tokio::{
    time::Instant,
    time::{interval, Duration},
};

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[derive(Error, Debug)]
enum Error {
    #[error(transparent)]
    CmdUtilError(#[from] CmdUtilError),
    #[error(transparent)]
    ImlManagerClientError(#[from] ImlManagerClientError),
    #[error(transparent)]
    ImlGraphqlQueriesError(#[from] iml_graphql_queries::Errors),
    #[error(transparent)]
    ImlPostgresError(#[from] iml_postgres::sqlx::Error),
}

#[derive(Debug, PartialEq, Eq, Hash, Clone)]
enum State {
    Monitoring(u64),
    CountingDown(Instant),
}

async fn tick(snapshot_client_counts: &mut HashMap<i32, State>, pool: PgPool) -> Result<(), Error> {
    let client: Client = iml_manager_client::get_client()?;
    let client_2 = client.clone();

    let query = iml_influx::filesystems::query();
    let stats_fut =
        get_influx::<iml_influx::filesystems::InfluxResponse>(client, "iml_stats", query.as_str());

    let influx_resp = stats_fut.await?;
    let stats = iml_influx::filesystems::Response::from(influx_resp);

    tracing::debug!("Influx stats: {:?}", stats);

    let snapshots =
        sqlx::query!("SELECT id, filesystem_name, snapshot_name, snapshot_fsname FROM snapshot")
            .fetch_all(&pool)
            .await?;
    tracing::debug!("Fetched {} snapshots from DB", snapshots.len());

    for snapshot in snapshots {
        let snapshot_id = snapshot.id;
        let snapshot_stats = match stats.get(&snapshot.snapshot_fsname) {
            Some(x) => x,
            None => continue,
        };

        let state = snapshot_client_counts.get_mut(&snapshot_id);
        let clients = snapshot_stats.clients.unwrap_or(0);

        match state {
            Some(State::Monitoring(prev_clients)) => {
                tracing::debug!(
                    "Monitoring. Snapshot {}: {} clients (previously {} clients)",
                    &snapshot.snapshot_fsname,
                    clients,
                    prev_clients,
                );
                if *prev_clients > 0 && clients == 0 {
                    tracing::trace!("counting down for job");
                    let instant = Instant::now() + Duration::from_secs(5 * 60);
                    state.map(|s| *s = State::CountingDown(instant));
                } else {
                    *prev_clients = clients;
                }
            }
            Some(State::CountingDown(when)) => {
                tracing::debug!(
                    "Counting down. Snapshot {}: 0 clients (previously {} clients)",
                    &snapshot.snapshot_fsname,
                    clients
                );
                if clients > 0 {
                    tracing::trace!("changing state");
                    state.map(|s| *s = State::Monitoring(clients));
                } else if Instant::now() >= *when {
                    tracing::trace!("running the job");
                    state.map(|s| *s = State::Monitoring(0));

                    let query = snapshot_queries::unmount::build(
                        &snapshot.filesystem_name,
                        &snapshot.snapshot_name,
                    );
                    let resp: iml_graphql_queries::Response<snapshot_queries::unmount::Resp> =
                        graphql(client_2.clone(), query).await?;
                    let command = Result::from(resp)?.data.unmount_snapshot;
                    wait_for_cmds_success(&[command], None).await?;
                }
            }
            None => {
                tracing::debug!(
                    "Just learnt about this snapshot. Snapshot {}: {} clients",
                    &snapshot.snapshot_fsname,
                    clients,
                );

                snapshot_client_counts.insert(snapshot_id, State::Monitoring(clients));
            }
        }
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<Vec<snapshot::Snapshot>>(&ch, "rust_agent_snapshot_rx");

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;
    let pool_2 = pool.clone();
    sqlx::migrate!("../../migrations").run(&pool).await?;

    tokio::spawn(async move {
        let mut interval = interval(Duration::from_secs(60));
        let mut snapshot_client_counts: HashMap<i32, State> = HashMap::new();

        while let Some(_) = interval.next().await {
            let tick_result = tick(&mut snapshot_client_counts, pool_2.clone()).await;
            if let Err(e) = tick_result {
                tracing::error!("Error during handling snapshot autounmount: {}", e);
            }
        }
    });

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
