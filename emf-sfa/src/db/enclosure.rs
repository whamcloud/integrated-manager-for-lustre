use crate::EmfSfaError;
use emf_change::{Deletions, Upserts};
use emf_postgres::sqlx;
use emf_wire_types::sfa::wbem_interop::SfaEnclosure;

pub async fn all(pool: &sqlx::PgPool) -> Result<Vec<SfaEnclosure>, EmfSfaError> {
    let xs = sqlx::query_as!(
        SfaEnclosure,
        r#"
        SELECT
            index,
            element_name,
            health_state as "health_state: _",
            health_state_reason,
            child_health_state as "child_health_state: _",
            model,
            position,
            enclosure_type as "enclosure_type: _",
            canister_location,
            storage_system
        FROM sfaenclosure"#,
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

pub async fn batch_upsert(
    x: Upserts<&SfaEnclosure>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let xs = x.0.into_iter().fold(
        (
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
        ),
        |mut acc, x| {
            acc.0.push(x.index);
            acc.1.push(x.element_name.to_string());
            acc.2.push(x.health_state as i16);
            acc.3.push(x.health_state_reason.to_string());
            acc.4.push(x.child_health_state as i16);
            acc.5.push(x.model.to_string());
            acc.6.push(x.position);
            acc.7.push(x.enclosure_type as i16);
            acc.8.push(x.canister_location.to_string());
            acc.9.push(x.storage_system.to_string());

            acc
        },
    );

    sqlx::query!(
        r#"
        INSERT INTO sfaenclosure
        (
            index,
            element_name,
            health_state,
            health_state_reason,
            child_health_state,
            model,
            position,
            enclosure_type,
            canister_location,
            storage_system
        )
        SELECT * FROM UNNEST(
            $1::integer[],
            $2::text[],
            $3::smallint[],
            $4::text[],
            $5::smallint[],
            $6::text[],
            $7::smallint[],
            $8::smallint[],
            $9::text[],
            $10::text[]
        )
        ON CONFLICT (index, storage_system) DO UPDATE
        SET
            child_health_state = excluded.child_health_state,
            element_name = excluded.element_name,
            health_state = excluded.health_state,
            health_state_reason = excluded.health_state_reason,
            position = excluded.position,
            enclosure_type = excluded.enclosure_type
    "#,
        &xs.0,
        &xs.1,
        &xs.2,
        &xs.3,
        &xs.4,
        &xs.5,
        &xs.6,
        &xs.7,
        &xs.8,
        &xs.9,
    )
    .execute(&pool)
    .await?;

    Ok(())
}

pub async fn batch_delete(
    xs: Deletions<&SfaEnclosure>,
    pool: sqlx::PgPool,
) -> Result<(), EmfSfaError> {
    let (indexes, storage_system): (Vec<_>, Vec<_>) =
        xs.0.into_iter()
            .map(|x| (x.index, x.storage_system.to_string()))
            .unzip();

    sqlx::query!(
        r#"
            DELETE from sfaenclosure
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
