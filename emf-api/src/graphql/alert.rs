// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::graphql::Context;
use chrono::Utc;
use emf_postgres::sqlx;
use emf_wire_types::{
    AlertRecordType, AlertResponse, AlertSeverity, AlertState, ComponentType, Meta, SortDir,
};
use juniper::{graphql_object, FieldError, Value};
use std::{convert::TryInto, ops::Deref};

pub(crate) struct AlertQuery;

#[graphql_object(Context = Context)]
impl AlertQuery {
    #[graphql(arguments(
        limit(description = "optional paging limit, defaults to 100",),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc"),
        message(
            description = "Pattern to search for in message. Uses Postgres pattern matching  (https://www.postgresql.org/docs/9.6/functions-matching.html)"
        ),
        active(description = "The active status of the alert"),
        start_datetime(description = "Start of the time period of logs"),
        end_datetime(description = "End of the time period of logs"),
        record_type(description = "The type of the alert"),
        severity(description = "Upper bound of alert severity. Defaults to `CRITICAL`"),
    ))]
    /// List `AlertState`s
    async fn list(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
        message: Option<String>,
        active: Option<bool>,
        start_datetime: Option<chrono::DateTime<Utc>>,
        end_datetime: Option<chrono::DateTime<Utc>>,
        record_type: Option<Vec<AlertRecordType>>,
        severity: Option<AlertSeverity>,
    ) -> juniper::FieldResult<AlertResponse> {
        let dir = dir.unwrap_or_default();

        let severity = severity.unwrap_or(AlertSeverity::CRITICAL) as i32;

        let record_type =
            record_type.map(|xs| xs.into_iter().map(|x| x.to_string()).collect::<Vec<_>>());

        let xs = sqlx::query_as!(
            AlertState,
            r#"
                    SELECT
                        id,
                        alert_item_type_id AS "alert_item_type_id: ComponentType",
                        alert_item_id,
                        alert_type,
                        "begin",
                        "end",
                        active,
                        dismissed,
                        severity AS "severity: AlertSeverity",
                        record_type AS "record_type: AlertRecordType",
                        variant,
                        lustre_pid,
                        message
                    FROM alertstate a
                    WHERE ($4::TEXT IS NULL OR a.message LIKE $4)
                      AND ($5::BOOL IS NULL OR a.active = $5)
                      AND ($6::TIMESTAMPTZ IS NULL OR a.begin >= $6)
                      AND ($7::TIMESTAMPTZ IS NULL OR a.end <= $7)
                      AND ($8::text[] IS NULL OR a.record_type::text = ANY($8::text[]))
                      AND a.severity <= $9
                    ORDER BY
                        CASE WHEN $3 = 'ASC' THEN a.begin END ASC,
                        CASE WHEN $3 = 'DESC' THEN a.begin END DESC
                    OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.map(|x| x as i64).unwrap_or(100),
            dir.deref(),
            message,
            active,
            start_datetime,
            end_datetime,
            record_type.as_ref().map(|xs| xs.as_slice()),
            severity,
        )
        .fetch_all(&context.pg_pool)
        .await?;

        let total_count =
            sqlx::query!("SELECT total_rows FROM rowcount WHERE table_name = 'alertstate'")
                .fetch_one(&context.pg_pool)
                .await?
                .total_rows
                .ok_or_else(|| {
                    FieldError::new("Number of rows doesn't fit in i32", Value::null())
                })?;

        Ok(AlertResponse {
            data: xs,
            meta: Meta {
                total_count: total_count.try_into()?,
            },
        })
    }
}
