// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::TimeZone;
use emf_journal::{execute_handlers, get_message_class, EmfJournalError};
use emf_manager_env::get_pool_limit;
use emf_postgres::get_db_pool;
use emf_service_queue::spawn_service_consumer;
use emf_tracing::tracing;
use emf_wire_types::JournalMessage;
use futures::StreamExt;
use lazy_static::lazy_static;
use sqlx::postgres::PgPool;
use std::convert::TryInto;

lazy_static! {
    static ref DBLOG_HW: i64 = emf_manager_env::get_dblog_hw() as i64;
    static ref DBLOG_LW: i64 = emf_manager_env::get_dblog_lw() as i64;
}

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

async fn purge_excess(pool: &PgPool, mut num_rows: i64) -> Result<i64, EmfJournalError> {
    if num_rows <= *DBLOG_HW {
        return Ok(num_rows);
    }

    while *DBLOG_LW < num_rows {
        let x = sqlx::query!(
            r#"
                DELETE FROM logmessage
                WHERE id in (
                    SELECT id FROM logmessage ORDER BY id LIMIT $1
                )
            "#,
            std::cmp::min(10_000, num_rows - *DBLOG_LW)
        )
        .execute(pool)
        .await?
        .rows_affected();

        num_rows -= x as i64;
        tracing::info!("Purged {} rows, current known row count is {}", x, num_rows);
    }

    Ok(num_rows)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pool = get_db_pool(
        get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT),
        emf_manager_env::get_port("JOURNAL_SERVICE_PG_PORT"),
    )
    .await?;

    let mut num_rows = sqlx::query!("SELECT COUNT(*) FROM logmessage")
        .fetch_one(&pool)
        .await?
        .count
        .expect("count returned None");

    let mut rx = spawn_service_consumer::<Vec<JournalMessage>>(emf_manager_env::get_port(
        "JOURNAL_SERVICE_PORT",
    ));

    while let Some((host, xs)) = rx.next().await {
        num_rows = purge_excess(&pool, num_rows).await?;

        let row = sqlx::query!("select id from host where fqdn = $1", host.to_string())
            .fetch_optional(&pool)
            .await?;

        let id = match row {
            Some(row) => row.id,
            None => {
                tracing::warn!("Host '{}' is unknown", host);

                continue;
            }
        };

        for x in xs.iter() {
            execute_handlers(&x.message, id, &pool).await?;
        }

        num_rows += xs.len() as i64;

        let x = xs.into_iter().fold(
            (vec![], vec![], vec![], vec![], vec![], vec![]),
            |mut acc, x| {
                acc.0.push(x.datetime);
                acc.1.push(x.severity as i16);
                acc.2.push(x.facility);
                acc.3.push(x.source);
                acc.5.push(get_message_class(&x.message) as i16);
                acc.4.push(x.message);

                acc
            },
        );

        let times =
            x.0.into_iter()
                .map(|t| {
                    let t = t.as_secs().try_into()?;

                    Ok(chrono::offset::Utc.timestamp(t, 0))
                })
                .collect::<Result<Vec<_>, EmfJournalError>>()?;

        sqlx::query!(
            r#"
             INSERT INTO logmessage
             (datetime, fqdn, severity, facility, tag, message, message_class)
             SELECT datetime, $2, severity, facility, source, message, message_class
             FROM UNNEST($1::timestamptz[], $3::smallint[], $4::smallint[], $5::text[], $6::text[], $7::smallint[])
             AS t(datetime, severity, facility, source, message, message_class)
         "#,
            times.as_slice(),
            host.to_string(),
            &x.1,
            &x.2,
            &x.3,
            &x.4,
            &x.5
        )
        .execute(&pool)
        .await?;
    }

    Ok(())
}
