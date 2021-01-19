// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::EmfSfaError;
use emf_change::{Deletions, Upserts};
use emf_postgres::sqlx;
use emf_wire_types::sfa::wbem_interop::{SfaPowerSupply, SfaPowerSupplyRow};
use unzip_n::unzip_n;

pub async fn all(pool: &sqlx::PgPool) -> Result<Vec<SfaPowerSupply>, EmfSfaError> {
    let xs = sqlx::query_as!(
        SfaPowerSupply,
        r#"
        SELECT
            index,
            enclosure_index,
            health_state as "health_state: _",
            health_state_reason,
            position,
            storage_system
        FROM chroma_core_sfapowersupply
        "#
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

unzip_n!(6);

pub async fn batch_upsert(
    x: Upserts<&SfaPowerSupply>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let xs =
        x.0.into_iter()
            .cloned()
            .map(SfaPowerSupplyRow::from)
            .unzip_n_vec();

    sqlx::query!(
        r#"
        INSERT INTO chroma_core_sfapowersupply
        (
            index,
            enclosure_index,
            health_state,
            health_state_reason,
            position,
            storage_system
        )
        SELECT * FROM UNNEST(
            $1::integer[],
            $2::integer[],
            $3::smallint[],
            $4::text[],
            $5::smallint[],
            $6::text[]
        )
        ON CONFLICT (index, storage_system, enclosure_index) DO UPDATE
        SET
            health_state = excluded.health_state,
            health_state_reason = excluded.health_state_reason,
            position = excluded.position
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

unzip_n!(3);

pub async fn batch_delete(
    xs: Deletions<&SfaPowerSupply>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let (indexes, storage_system, enclosure_indexes): (Vec<i32>, Vec<String>, Vec<i32>) =
        xs.0.into_iter()
            .map(|x| (x.index, x.storage_system.to_string(), x.enclosure_index))
            .unzip_n();

    sqlx::query!(
        r#"
            DELETE from chroma_core_sfapowersupply
            WHERE (index, storage_system, enclosure_index)
            IN (
                SELECT *
                FROM UNNEST($1::int[], $2::text[], $3::int[])
            )
        "#,
        &indexes,
        &storage_system,
        &enclosure_indexes
    )
    .execute(&pool)
    .await?;

    Ok(())
}
