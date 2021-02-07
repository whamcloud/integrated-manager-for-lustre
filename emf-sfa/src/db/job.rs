// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::EmfSfaError;
use emf_change::{Deletions, Upserts};
use emf_postgres::sqlx;
use emf_wire_types::sfa::wbem_interop::{SfaJob, SfaJobRow};
use unzip_n::unzip_n;

unzip_n!(6);

pub async fn all(pool: &sqlx::PgPool) -> Result<Vec<SfaJob>, EmfSfaError> {
    let xs = sqlx::query_as!(
        SfaJob,
        r#"
        SELECT
            index,
            sub_target_index,
            sub_target_type as "sub_target_type: _",
            job_type as "job_type: _",
            state as "state: _",
            storage_system
        FROM sfajob
    "#
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

pub async fn batch_upsert(x: Upserts<&SfaJob>, pool: sqlx::PgPool) -> Result<(), EmfSfaError> {
    let xs = x.0.into_iter().cloned().map(SfaJobRow::from).unzip_n_vec();

    sqlx::query!(
        r#"
        INSERT INTO sfajob
        (
            index,
            sub_target_index,
            sub_target_type,
            job_type,
            state,
            storage_system
        )
        SELECT * FROM UNNEST(
            $1::integer[],
            $2::integer[],
            $3::smallint[],
            $4::smallint[],
            $5::smallint[],
            $6::text[]
        )
        ON CONFLICT (index, storage_system) DO UPDATE
        SET
            sub_target_index = excluded.sub_target_index,
            sub_target_type = excluded.sub_target_type,
            job_type = excluded.job_type,
            state = excluded.state
    "#,
        &xs.0,
        &xs.1 as &[Option<i32>],
        &xs.2 as &[Option<i16>],
        &xs.3,
        &xs.4,
        &xs.5,
    )
    .execute(&pool)
    .await?;

    Ok(())
}

pub async fn batch_delete(xs: Deletions<&SfaJob>, pool: sqlx::PgPool) -> Result<(), EmfSfaError> {
    let (indexes, storage_system): (Vec<_>, Vec<_>) =
        xs.0.into_iter()
            .map(|x| (x.index, x.storage_system.to_string()))
            .unzip();

    sqlx::query!(
        r#"
            DELETE from sfajob
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
