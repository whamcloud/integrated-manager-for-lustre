// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::Fqdn;
use sqlx::{Error as SqlxError, PgPool};

pub async fn get_host_id_by_fqdn(fqdn: &Fqdn, pool: &PgPool) -> Result<Option<i32>, SqlxError> {
    let id = sqlx::query!(
        "SELECT id FROM chroma_core_managedhost WHERE fqdn = $1 AND not_deleted = 't'",
        fqdn.to_string()
    )
    .fetch_optional(pool)
    .await?
    .map(|x| x.id);

    Ok(id)
}
