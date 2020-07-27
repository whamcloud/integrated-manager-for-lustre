// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ActionRunnerError;
use iml_postgres::sqlx;
use std::collections::HashMap;

// pub(crate) async fn get_host_fqdn_by_id(
//     id: i32,
//     pool: sqlx::PgPool,
// ) -> Result<Option<String>, ActionRunnerError> {
//     let fqdn = sqlx::query!(
//         r#"SELECT fqdn FROM chroma_core_managedhost
//         WHERE id = $1 AND not_deleted = 't'"#,
//         id
//     )
//     .fetch_optional(&pool)
//     .await?
//     .map(|x| x.fqdn);

//     Ok(fqdn)
// }

pub(crate) async fn get_mgs_host_fqdn(
    pool: &sqlx::PgPool,
) -> Result<HashMap<String, String>, ActionRunnerError> {
    let map = sqlx::query!(
        "SELECT mh.fqdn, target.filesystems FROM target as target \
            LEFT JOIN chroma_core_managedhost as mh ON mh.id = target.active_host_id \
            WHERE target.name='MGS' AND mh.fqdn IS NOT NULL"
    )
    .fetch_all(pool)
    .await?
    .into_iter()
    .map(|x| {
        let xs = x
            .filesystems
            .iter()
            .cloned()
            .map(|fs| (fs, x.fqdn.to_string()))
            .collect::<Vec<(String, String)>>();
        xs
    })
    .flatten()
    .collect::<HashMap<String, String>>();

    Ok(map)
}
