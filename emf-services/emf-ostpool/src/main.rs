// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_ostpool::{db, error::Error};
use emf_postgres::sqlx;
use emf_service_queue::spawn_service_consumer;
use emf_tracing::tracing;
use emf_wire_types::FsPoolMap;
use futures::{future::try_join_all, StreamExt};
use std::collections::BTreeSet;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let mut rx =
        spawn_service_consumer::<FsPoolMap>(emf_manager_env::get_port("OSTPOOL_SERVICE_PORT"));

    let db_pool =
        emf_postgres::get_db_pool(2, emf_manager_env::get_port("OSTPOOL_SERVICE_PG_PORT")).await?;

    while let Some((fqdn, fspools)) = rx.next().await {
        tracing::debug!("Pools from {}: {:?}", fqdn, fspools);

        let db_pool = db_pool.clone();

        let xs = fspools.iter().map(move |(fsname, newpoolset)| {
            let db_pool = db_pool.clone();

            async move {
                // If fsid finds no match, assume FS hasn't been added to EMF and skip
                let row = sqlx::query!("SELECT id FROM filesystem WHERE name = $1", &fsname)
                    .fetch_optional(&db_pool)
                    .await?;

                let fsid = match row {
                    Some(x) => x.id,
                    None => {
                        tracing::info!("Filesystem {} not found in DB", &fsname);

                        return Ok(vec![]);
                    }
                };

                tracing::debug!("{}: {:?}", fsname, newpoolset);

                let oldpoolset = db::poolset(fsname, fsid, &db_pool).await?;

                let addset: BTreeSet<_> = newpoolset.difference(&oldpoolset).cloned().collect();

                let xsadd = addset.clone().into_iter().map(|pool| {
                    let db_pool = db_pool.clone();

                    async move {
                        tracing::debug!("Create {}.{}: {:?}", fsname, &pool.name, &pool.osts);

                        let poolid = db::create(fsid, &pool.name, &db_pool).await?;

                        db::grow(&fsname, poolid, &pool.osts, &db_pool).await
                    }
                });

                let xsrm = oldpoolset.difference(&newpoolset).cloned().map(|pool| {
                    let db_pool = db_pool.clone();

                    async move {
                        if let Some(poolid) = db::poolid(fsid, &pool.name, &db_pool).await? {
                            tracing::debug!("Remove {}.{}: {:?}", fsname, &pool.name, &pool.osts);

                            db::shrink(&fsname, poolid, &pool.osts, &db_pool).await?;
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

                                    db::diff(&fsname, poolid, &pool.osts, &db_pool).await
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
