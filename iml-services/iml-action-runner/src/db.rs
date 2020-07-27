// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ActionRunnerError;
use iml_postgres::sqlx;

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

pub(crate) async fn get_mgs_host_fqdn(
    pool: sqlx::PgPool,
) -> Result<Option<String>, ActionRunnerError> {
    let fqdn = sqlx::query!(
        "SELECT mh.fqdn FROM targets as targets \
            LEFT JOIN chroma_core_managedhost as mh ON mh.id = targets.active_host_id \
            WHERE targets.name='MGS'"
    )
    .fetch_optional(&pool)
    .await?
    .map(|x| x.fqdn);

    Ok(fqdn)
}
