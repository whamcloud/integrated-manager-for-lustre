// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ActionRunnerError;
use emf_postgres::sqlx;

pub(crate) async fn get_host_fqdn_by_id(
    id: i32,
    pool: sqlx::PgPool,
) -> Result<Option<String>, ActionRunnerError> {
    let fqdn = sqlx::query!(
        "select fqdn from chroma_core_managedhost where id = $1 and not_deleted = 't'",
        id
    )
    .fetch_optional(&pool)
    .await?
    .map(|x| x.fqdn);

    Ok(fqdn)
}
