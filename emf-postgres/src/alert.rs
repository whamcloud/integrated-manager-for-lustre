// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::{AlertRecordType, AlertSeverity};
use sqlx::PgPool;

pub async fn lower(
    pool: &PgPool,
    xs: Vec<AlertRecordType>,
    host_id: i32,
) -> Result<(), sqlx::Error> {
    let xs: Vec<_> = xs.iter().map(|x| x.to_string()).collect();

    sqlx::query!(
        r#"UPDATE chroma_core_alertstate
            SET active = Null, "end" = now()
            WHERE
                active = true
                AND alert_item_id = $1
                AND record_type = ANY($2)
        "#,
        host_id,
        &xs
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn raise(
    pool: &PgPool,
    record_type: AlertRecordType,
    msg: String,
    item_content_type_id: i32,
    lustre_pid: Option<i32>,
    severity: AlertSeverity,
    item_id: i32,
) -> Result<(), sqlx::Error> {
    let record_type = record_type.to_string();
    let severity: i32 = severity.into();

    sqlx::query!(
        r#"INSERT INTO chroma_core_alertstate
        (
            record_type,
            variant,
            alert_item_id,
            alert_type,
            begin,
            message,
            active,
            dismissed,
            severity,
            lustre_pid,
            alert_item_type_id
        )
        VALUES ($1, '{}', $2, $1, now(), $3, true, false, $4, $5, $6)
        ON CONFLICT DO NOTHING
        "#,
        &record_type,
        item_id,
        msg,
        severity,
        lustre_pid,
        item_content_type_id
    )
    .execute(pool)
    .await?;

    Ok(())
}
