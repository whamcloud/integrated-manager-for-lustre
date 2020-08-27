// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future::try_join_all, TryStreamExt};
use iml_ostpool::{db, error::Error};
use iml_postgres::sqlx;
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::FsPoolMap;
use std::collections::BTreeSet;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let db_pool = iml_postgres::get_db_pool(2).await?;

    let pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let pool_type_id: i32 = sqlx::query!(
        r#"
            SELECT id FROM django_content_type 
            WHERE app_label = 'chroma_core' AND model = 'ostpool'
            "#
    )
    .fetch_one(&db_pool)
    .await?
    .id;

    let mut s = consume_data::<FsPoolMap>(&ch, "rust_agent_ostpool_rx");

    while let Some((fqdn, fspools)) = s.try_next().await? {
        tracing::debug!("Pools from {}: {:?}", fqdn, fspools);

        let db_pool = db_pool.clone();

        let xs = fspools.iter().map(move |(fsname, newpoolset)| {
            let db_pool = db_pool.clone();

            async move {
                // If fsid finds no match, assume FS hasn't been added to IML and skip
                let fsid = match db::fsid(&fsname, &db_pool).await {
                    Ok(id) => id,
                    Err(Error::NotFound) => {
                        tracing::info!("Filesystem {} not found in DB", &fsname);
                        return Ok(vec![]);
                    }
                    Err(e) => return Err(e),
                };
                tracing::debug!("{}: {:?}", fsname, newpoolset);

                let oldpoolset = db::poolset(fsname, fsid, &db_pool).await?;

                let addset: BTreeSet<_> = newpoolset.difference(&oldpoolset).cloned().collect();

                let xsadd = addset.clone().into_iter().map(|pool| {
                    let db_pool = db_pool.clone();

                    async move {
                        tracing::debug!("Create {}.{}: {:?}", fsname, &pool.name, &pool.osts);

                        let poolid = db::create(fsid, pool_type_id, &pool.name, &db_pool).await?;

                        db::grow(fsid, poolid, &pool.osts, &db_pool).await
                    }
                });

                let xsrm = oldpoolset.difference(&newpoolset).cloned().map(|pool| {
                    let db_pool = db_pool.clone();

                    async move {
                        if let Some(poolid) = db::poolid(fsid, &pool.name, &db_pool).await? {
                            tracing::debug!("Remove {}.{}: {:?}", fsname, &pool.name, &pool.osts);

                            db::shrink(fsid, poolid, &pool.osts, &db_pool).await?;
                            db::delete(fsid, &pool.name, &db_pool).await?;
                        }

                        Ok::<_, Error>(())
                    }
                });

                let xsupdate = newpoolset.difference(&addset).cloned().filter_map(|pool| {
                    if let Some(old) = oldpoolset.get(&pool) {
                        if old.osts != pool.osts {
                            let db_pool = db_pool.clone();

                            return Some(async move {
                                if let Some(poolid) = db::poolid(fsid, &pool.name, &db_pool).await?
                                {
                                    tracing::debug!(
                                        "Diff {}.{}: {:?}",
                                        fsname,
                                        &pool.name,
                                        &pool.osts
                                    );

                                    db::diff(fsid, poolid, &pool.osts, &db_pool).await
                                } else {
                                    Ok(())
                                }
                            });
                        }
                    }
                    None
                });

                try_join_all(xsadd).await?;
                try_join_all(xsrm).await?;
                try_join_all(xsupdate).await
            }
        });

        try_join_all(xs).await?;
    }

    Ok(())
}
