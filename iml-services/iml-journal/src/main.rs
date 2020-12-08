// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::TimeZone;
use futures::TryStreamExt;
use iml_journal::{execute_handlers, get_message_class, ImlJournalError};
use iml_manager_env::get_pool_limit;
use iml_postgres::{
    get_db_pool,
    sqlx::{self, Done, PgPool},
};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::JournalMessage;
use lazy_static::lazy_static;
use std::convert::TryInto;

lazy_static! {
    static ref DBLOG_HW: i64 = iml_manager_env::get_dblog_hw() as i64;
    static ref DBLOG_LW: i64 = iml_manager_env::get_dblog_lw() as i64;
}

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

async fn purge_excess(pool: &PgPool, mut num_rows: i64) -> Result<i64, ImlJournalError> {
    if num_rows <= *DBLOG_HW {
        return Ok(num_rows);
    }

    while *DBLOG_LW < num_rows {
        let x = sqlx::query!(
            r#"
                DELETE FROM chroma_core_logmessage
                WHERE id in ( 
                    SELECT id FROM chroma_core_logmessage ORDER BY id LIMIT $1
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
    iml_tracing::init();

    tracing::info!("Starting");

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;

    let rabbit_pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(rabbit_pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<Vec<JournalMessage>>(&ch, "rust_agent_journal_rx");

    let mut num_rows = sqlx::query!("SELECT COUNT(*) FROM chroma_core_logmessage")
        .fetch_one(&pool)
        .await?
        .count
        .expect("count returned None");

    while let Some((host, xs)) = s.try_next().await? {
        num_rows = purge_excess(&pool, num_rows).await?;

        struct Row {
            id: i32,
            content_type_id: Option<i32>,
        }

        let row = sqlx::query_as!(Row,
            "select id, content_type_id from chroma_core_managedhost where fqdn = $1 and not_deleted = 't'",
            host.to_string()
        )
        .fetch_optional(&pool)
        .await?;

        let row = match row {
            Some(row) => row,
            None => {
                tracing::warn!("Host '{}' is unknown", host);

                continue;
            }
        };

        let content_type_id = match row.content_type_id.as_ref() {
            Some(x) => *x,
            None => {
                tracing::warn!("Host '{}' content_type_id  is unknown", host);
                continue;
            }
        };

        for x in xs.iter() {
            execute_handlers(&x.message, row.id, content_type_id, &pool).await?;
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
                .collect::<Result<Vec<_>, ImlJournalError>>()?;

        sqlx::query!(
            r#"
             INSERT INTO chroma_core_logmessage
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
