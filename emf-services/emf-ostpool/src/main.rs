// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![type_length_limit = "5657938"]

use emf_ostpool::{db, error::Error};
use emf_service_queue::service_queue::consume_data;
use emf_wire_types::FsPoolMap;
use futures::{future::try_join_all, TryStreamExt};
use std::collections::BTreeSet;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pool = emf_rabbit::connect_to_rabbit(1);

    let conn = emf_rabbit::get_conn(pool).await?;

    let ch = emf_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<FsPoolMap>(&ch, "rust_agent_ostpool_rx");

    while let Some((fqdn, fspools)) = s.try_next().await? {
        tracing::debug!("Pools from {}: {:?}", fqdn, fspools);

        let client = db::connect(fqdn).await?;

        let xs = fspools.iter().map(|(fsname, newpoolset)| {
            let client = client.clone();

            async move {
                // If fsid finds no match, assume FS hasn't been added to EMF and skip
                let fsid = match client.fsid(&fsname).await {
                    Ok(id) => id,
                    Err(Error::NotFound) => {
                        tracing::info!("Filesystem {} not found in DB", &fsname);
                        return Ok(vec![]);
                    }
                    Err(e) => return Err(e),
                };
                tracing::debug!("{}: {:?}", fsname, newpoolset);

                let oldpoolset = client.poolset(fsname, fsid).await?;

                let addset: BTreeSet<_> = newpoolset.difference(&oldpoolset).cloned().collect();

                let xsadd = addset.clone().into_iter().map(|pool| {
                    let client = client.clone();
                    async move {
                        tracing::debug!("Create {}.{}: {:?}", fsname, &pool.name, &pool.osts);
                        let poolid = client.create(fsid, &pool.name).await?;
                        client.grow(fsid, poolid, &pool.osts).await
                    }
                });

                let xsrm = oldpoolset.difference(&newpoolset).cloned().map(|pool| {
                    let client = client.clone();
                    async move {
                        if let Some(poolid) = client.poolid(fsid, &pool.name).await? {
                            tracing::debug!("Remove {}.{}: {:?}", fsname, &pool.name, &pool.osts);
                            client.shrink(fsid, poolid, &pool.osts).await?;
                            client.delete(fsid, &pool.name).await?;
                        }
                        Ok::<_, Error>(())
                    }
                });

                let xsupdate = newpoolset.difference(&addset).cloned().filter_map(|pool| {
                    if let Some(old) = oldpoolset.get(&pool) {
                        if old.osts != pool.osts {
                            let client = client.clone();
                            return Some(async move {
                                if let Some(poolid) = client.poolid(fsid, &pool.name).await? {
                                    tracing::debug!(
                                        "Diff {}.{}: {:?}",
                                        fsname,
                                        &pool.name,
                                        &pool.osts
                                    );
                                    client.diff(fsid, poolid, &pool.osts).await
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
