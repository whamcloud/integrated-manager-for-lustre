// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures_util::stream::TryStreamExt;
use iml_manager_env::get_pool_limit;
use iml_postgres::{get_db_pool, sqlx};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::snapshot;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<Vec<snapshot::Snapshot>>(&ch, "rust_agent_snapshot_rx");

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;
    sqlx::migrate!("../../migrations").run(&pool).await?;

    // tokio::spawn(
    //     async move {
    //         while let Some(m) = s.try_next().await? {
    //             tracing::debug!("Incoming message from agent: {:?}", m);

    //             let conn = iml_rabbit::get_conn(pool.clone()).await?;

    //             handle_agent_data(conn, m, Arc::clone(&sessions), Arc::clone(&rpcs))
    //                 .await
    //                 .unwrap_or_else(drop);
    //         }

    //         Ok(())
    //     }
    //     .map_err(|e: ImlServiceQueueError| {
    //         tracing::error!("{}", e);
    //     })
    //     .map(drop),
    // );

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
