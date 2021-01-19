// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::EmfSfaError;
use emf_postgres::{sqlx, PgPool};
use emf_wire_types::sfa::wbem_interop::SfaStorageSystem;

pub async fn upsert(x: SfaStorageSystem, pool: &PgPool) -> Result<(), EmfSfaError> {
    let SfaStorageSystem {
        uuid,
        platform,
        health_state_reason,
        health_state,
        child_health_state,
    } = x;

    sqlx::query!(
        r#"
        INSERT INTO chroma_core_sfastoragesystem
        (
            uuid,
            platform,
            health_state_reason,
            health_state,
            child_health_state
        )
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (uuid) DO UPDATE
        SET
            platform = excluded.platform,
            health_state_reason = excluded.health_state_reason,
            health_state = excluded.health_state,
            child_health_state = excluded.child_health_state
    "#,
        uuid,
        platform,
        health_state_reason,
        health_state as i16,
        child_health_state as i16,
    )
    .execute(pool)
    .await?;

    Ok(())
}
