use crate::EmfSfaError;
use emf_change::{Deletions, Upserts};
use emf_postgres::sqlx;
use emf_wire_types::sfa::wbem_interop::{SfaDiskDrive, SfaDiskDriveRow};
use unzip_n::unzip_n;

unzip_n!(9);

pub async fn all(pool: &sqlx::PgPool) -> Result<Vec<SfaDiskDrive>, EmfSfaError> {
    let xs = sqlx::query_as!(
        SfaDiskDrive,
        r#"SELECT 
                index,
                enclosure_index,
                failed,
                slot_number,
                health_state  as "health_state: _",
                health_state_reason,
                member_index,
                member_state as "member_state: _",
                storage_system
            FROM sfadiskdrive"#
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

pub async fn batch_upsert(
    x: Upserts<&SfaDiskDrive>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let xs =
        x.0.into_iter()
            .cloned()
            .map(SfaDiskDriveRow::from)
            .unzip_n_vec();

    sqlx::query!(
        r#"
        INSERT INTO sfadiskdrive
        (
            index,
            enclosure_index,
            failed,
            slot_number,
            health_state,
            health_state_reason,
            member_index,
            member_state,
            storage_system
        )
        SELECT * FROM UNNEST(
            $1::integer[],
            $2::integer[],
            $3::bool[],
            $4::integer[],
            $5::smallint[],
            $6::text[],
            $7::smallint[],
            $8::smallint[],
            $9::text[]
        )
        ON CONFLICT (index, storage_system) DO UPDATE
        SET
            enclosure_index = excluded.enclosure_index,
            failed = excluded.failed,
            slot_number = excluded.slot_number,
            health_state = excluded.health_state,
            health_state_reason = excluded.health_state_reason,
            member_index = excluded.member_index,
            member_state = excluded.member_state
    "#,
        &xs.0,
        &xs.1,
        &xs.2,
        &xs.3,
        &xs.4,
        &xs.5,
        &xs.6 as &[Option<i16>],
        &xs.7,
        &xs.8,
    )
    .execute(&pool)
    .await?;

    Ok(())
}

pub async fn batch_delete(
    xs: Deletions<&SfaDiskDrive>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let (indexes, storage_system): (Vec<_>, Vec<_>) =
        xs.0.into_iter()
            .map(|x| (x.index, x.storage_system.to_string()))
            .unzip();

    sqlx::query!(
        r#"
            DELETE from sfadiskdrive
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
