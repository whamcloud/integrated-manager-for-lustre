// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use core::fmt::Debug;
use futures_util::stream::TryStreamExt;
use iml_manager_env::get_pool_limit;
use iml_postgres::{get_db_pool, sqlx};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::snapshot;
use reqwest::{Client, Url};
use serde::de::DeserializeOwned;
use std::{collections::HashSet, sync::Arc};
use tokio::{
    sync::Mutex,
    time::{interval, Duration},
};

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[derive(Debug, thiserror::Error)]
enum ThisError {
    #[error(transparent)]
    Reqwest(#[from] reqwest::Error),
    #[error(transparent)]
    Url(#[from] url::ParseError),
    #[error(transparent)]
    Header(#[from] reqwest::header::InvalidHeaderValue),
}

async fn get_influx<T: DeserializeOwned + Debug>(
    client: Client,
    db: &str,
    q: &str,
) -> Result<T, ThisError> {
    let url = Url::parse(&iml_manager_env::get_manager_url())?.join("/influx")?;
    let resp = client
        .get(url)
        .query(&[("db", db), ("q", q)])
        .send()
        .await?
        .error_for_status()?;

    let json = resp.json().await?;

    tracing::debug!("Resp: {:?}", json);

    Ok(json)
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

    let snapshot_fsnames = Arc::new(Mutex::new(HashSet::new()));

    {
        let snapshot_fsnames = snapshot_fsnames.clone();
        tokio::spawn(async move {
            let mut interval = interval(Duration::from_secs(10));

            use tokio::stream::StreamExt;
            while let Some(_) = interval.next().await {
                let client: Client = iml_manager_client::get_client().unwrap();

                let query = iml_influx::filesystems::query();
                let fut_st = get_influx::<iml_influx::filesystems::InfluxResponse>(
                    client,
                    "iml_stats",
                    query.as_str(),
                );

                let influx_resp = fut_st.await.unwrap();
                let st = iml_influx::filesystems::Response::from(influx_resp);

                tracing::debug!("ST: {:?}", st);

                for (fs, st) in st {
                    if snapshot_fsnames.lock().await.get(&fs).is_some() {
                        tracing::info!("snapshot: {}, Clients: {}", fs, st.clients.unwrap_or(0));
                    }
                }
            }
        });
    }

    while let Some((fqdn, snapshots)) = s.try_next().await? {
        tracing::debug!("snapshots from {}: {:?}", fqdn, snapshots);

        let snaps = {
            let mut snapshot_fsnames = snapshot_fsnames.lock().await;

            snapshot_fsnames.clear();

            snapshots.into_iter().fold(
                (vec![], vec![], vec![], vec![], vec![], vec![], vec![]),
                |mut acc, s| {
                    acc.0.push(s.filesystem_name);
                    acc.1.push(s.snapshot_name);
                    acc.2.push(s.create_time.naive_utc());
                    acc.3.push(s.modify_time.naive_utc());
                    acc.4.push(s.snapshot_fsname.clone());
                    acc.5.push(s.mounted);
                    acc.6.push(s.comment);

                    snapshot_fsnames.insert(s.snapshot_fsname.clone());

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
