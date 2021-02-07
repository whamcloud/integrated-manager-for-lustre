// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::EmfSfaError;
use emf_change::{Deletions, Upserts};
use emf_postgres::sqlx;
use emf_wire_types::sfa::wbem_interop::{SfaController, SfaControllerRow};
use unzip_n::unzip_n;

pub async fn all(pool: &sqlx::PgPool) -> Result<Vec<SfaController>, EmfSfaError> {
    let xs = sqlx::query_as!(
        SfaController,
        r#"
        SELECT 
            index,
            enclosure_index,
            health_state as "health_state: _",
            health_state_reason,
            child_health_state as "child_health_state: _",
            storage_system
        FROM sfacontroller
        "#
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

unzip_n!(6);

pub async fn batch_upsert(
    x: Upserts<&SfaController>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let xs =
        x.0.into_iter()
            .cloned()
            .map(SfaControllerRow::from)
            .unzip_n_vec();

    sqlx::query!(
        r#"
        INSERT INTO sfacontroller
        (
            index,
            enclosure_index,
            health_state,
            health_state_reason,
            child_health_state,
            storage_system
        )
        SELECT * FROM UNNEST(
            $1::int[],
            $2::int[],
            $3::smallint[],
            $4::text[],
            $5::smallint[],
            $6::text[]
        )
        ON CONFLICT (index, storage_system) DO UPDATE
        SET
            enclosure_index = excluded.enclosure_index,
            health_state = excluded.health_state,
            health_state_reason = excluded.health_state_reason,
            child_health_state = excluded.child_health_state
    "#,
        &xs.0,
        &xs.1,
        &xs.2,
        &xs.3,
        &xs.4,
        &xs.5,
    )
    .execute(&pool)
    .await?;

    Ok(())
}

pub async fn batch_delete(
    xs: Deletions<&SfaController>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let (indexes, storage_system): (Vec<i32>, Vec<String>) =
        xs.0.into_iter()
            .map(|x| (x.index, x.storage_system.to_string()))
            .unzip();

    sqlx::query!(
        r#"
            DELETE from sfacontroller
            WHERE (index, storage_system)
            IN (
                SELECT *
                FROM UNNEST($1::int[], $2::text[])
            )
        "#,
        &indexes,
        &storage_system
    )
    .execute(&pool)
    .await?;

    Ok(())
}
