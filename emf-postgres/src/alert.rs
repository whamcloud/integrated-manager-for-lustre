// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::{AlertRecordType, AlertSeverity, ComponentType};
use sqlx::PgPool;

pub async fn lower(
    pool: &PgPool,
    xs: Vec<AlertRecordType>,
    host_id: i32,
) -> Result<(), sqlx::Error> {
    let xs: Vec<_> = xs.iter().map(|x| x.to_string()).collect();

    sqlx::query!(
        r#"UPDATE alertstate
            SET active = false, "end" = now()
            WHERE
                active = true
                AND alert_item_id = $1
                AND record_type::text = ANY($2)
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
    component_type: ComponentType,
    lustre_pid: Option<i32>,
    severity: AlertSeverity,
    item_id: i32,
) -> Result<(), sqlx::Error> {
    let severity: i32 = severity as i32;

    sqlx::query!(
        r#"INSERT INTO alertstate
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
        VALUES ($1::alert_record_type, '{}', $2, $1, now(), $3, true, false, $4, $5, $6)
        ON CONFLICT ON CONSTRAINT unique_active_alert DO NOTHING
        "#,
        record_type as AlertRecordType,
        item_id,
        msg,
        severity,
        lustre_pid,
        component_type as ComponentType
    )
    .execute(pool)
    .await?;

    Ok(())
}
