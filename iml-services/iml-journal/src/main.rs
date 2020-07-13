// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryStreamExt;
use iml_journal::{execute_handlers, get_message_class, ImlJournalError};
use iml_postgres::{get_db_pool, sqlx};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::JournalMessage;
use std::convert::TryInto;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    tracing::info!("Starting");

    let pool = get_db_pool().await?;

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
        tracing::info!("{:?}", xs);

        struct Row {
            id: i32,
            content_type_id: i32,
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

                return Ok(());
            }
        };

        for x in xs.iter() {
            execute_handlers(&x.message, row.id, row.content_type_id, &pool).await?;
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

                    Ok(time::OffsetDateTime::from_unix_timestamp(t))
                })
                .collect::<Result<Vec<time::OffsetDateTime>, ImlJournalError>>()?;

        sqlx::query!(
            r#"
             INSERT INTO chroma_core_logmessage
             (datetime, fqdn, severity, facility, tag, message, message_class)
             SELECT datetime, $2, severity, facility, source, message, message_class
             FROM UNNEST($1::timestamptz[], $3::smallint[], $4::smallint[], $5::text[], $6::text[], $7::smallint[])
             AS t(datetime, severity, facility, source, message, message_class)
         "#,
            &times,
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
