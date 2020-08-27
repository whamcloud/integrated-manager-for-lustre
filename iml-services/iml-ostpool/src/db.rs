// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::Error;
use futures::{future::try_join_all, TryStreamExt};
use iml_postgres::{sqlx, PgPool};
use iml_wire_types::OstPool;
use std::collections::BTreeSet;

/// Assume that if there is a single filesystem with a given name,
/// that it's the correct one
pub async fn fsid(fsname: &str, db_pool: &PgPool) -> Result<i32, Error> {
    let x = sqlx::query!(
        "SELECT id FROM chroma_core_managedfilesystem WHERE name=$1 AND not_deleted=True",
        fsname
    )
    .fetch_one(db_pool)
    .await?
    .id;

    Ok(x)
}

pub async fn poolid(fsid: i32, pn: &str, db_pool: &PgPool) -> Result<Option<i32>, Error> {
    let x = sqlx::query!("SELECT id FROM chroma_core_ostpool WHERE name=$1 AND filesystem_id=$2 AND not_deleted=True", pn, fsid)
        .fetch_optional(db_pool)
        .await?
        .map(|x| x.id);

    Ok(x)
}

/// Returns a poolset for a given filesystem, but osts element is always empty
pub async fn poolset(
    fsname: &str,
    fsid: i32,
    db_pool: &PgPool,
) -> Result<BTreeSet<OstPool>, Error> {
    let bs = sqlx::query!(
        "SELECT name FROM chroma_core_ostpool WHERE not_deleted=True AND filesystem_id=$1",
        fsid
    )
    .fetch(db_pool)
    .map_ok(|x| {
        let filesystem = fsname.to_string();

        OstPool {
            filesystem,
            name: x.name,
            osts: vec![],
        }
    })
    .try_collect()
    .await?;

    Ok(bs)
}

async fn ostid(fsid: i32, ost: &str, db_pool: &PgPool) -> Result<Option<i32>, Error> {
    let x = sqlx::query!(
        r#"SELECT managedtarget_ptr_id
                FROM chroma_core_managedost AS MO
                INNER JOIN chroma_core_managedtarget AS MT
                ON MO.managedtarget_ptr_id = MT.id
                WHERE filesystem_id = $1 AND name = $2 AND not_deleted=True"#,
        &fsid,
        &ost
    )
    .fetch_optional(db_pool)
    .await?
    .map(|x| x.managedtarget_ptr_id);

    Ok(x)
}

pub async fn create(
    fsid: i32,
    pool_type_id: i32,
    pn: &str,
    db_pool: &PgPool,
) -> Result<i32, Error> {
    let x = sqlx::query!(
            "INSERT INTO chroma_core_ostpool (name, content_type_id, filesystem_id, not_deleted) VALUES ($1, $2, $3, 't') RETURNING id",
            pn, pool_type_id, fsid
        ).fetch_one(db_pool)
        .await?
        .id;

    Ok(x)
}

pub async fn delete(fsid: i32, pn: &str, db_pool: &PgPool) -> Result<(), Error> {
    sqlx::query!(
        "UPDATE chroma_core_ostpool SET not_deleted = NULL WHERE filesystem_id = $1 AND name = $2",
        fsid,
        pn
    )
    .execute(db_pool)
    .await?;

    Ok(())
}

pub async fn grow(fsid: i32, poolid: i32, osts: &[String], db_pool: &PgPool) -> Result<(), Error> {
    let xs = osts.iter().map(|o| {
        async move {
            if let Some(ostid) = ostid(fsid, &o, db_pool).await? {
                let exists = sqlx::query!(
                    "SELECT id FROM chroma_core_ostpool_osts WHERE ostpool_id = $1 AND managedost_id = $2",
                    poolid,
                    ostid
                )
                .fetch_optional(db_pool)
                .await?
                .is_some();

                if exists {
                    tracing::debug!("Growing ({}).({}): ost:{}({})", fsid, poolid, o, ostid);

                    sqlx::query!("INSERT INTO chroma_core_ostpool_osts (ostpool_id, managedost_id) VALUES ($1, $2)",
                        poolid, ostid)
                    .execute(db_pool)
                    .await?;

                    Ok::<_, Error>(())
                } else {
                    tracing::debug!("Grow ({}).({}): ost:{} already exists", fsid, poolid, o);

                    Ok(())
                }
            } else {
                tracing::warn!("Failed Grow ({}).({}): ost:{} missing", fsid, poolid, o);

                Ok(())
            }
        }
    });

    try_join_all(xs).await?;

    Ok(())
}

pub async fn shrink(
    fsid: i32,
    poolid: i32,
    osts: &[String],
    db_pool: &PgPool,
) -> Result<(), Error> {
    let xs = osts.iter().map(|o| async move {
        if let Some(ostid) = ostid(fsid, &o, db_pool).await? {
            tracing::debug!("Shrinking ({}).({}): ost:{}({})", fsid, poolid, o, ostid);

            sqlx::query!(
                "DELETE FROM chroma_core_ostpool_osts WHERE ostpool_id = $1 AND managedost_id = $2",
                poolid,
                ostid
            )
            .execute(db_pool)
            .await?;

            Ok::<_, Error>(())
        } else {
            tracing::warn!("Failed Shrink ({}).({}): ost:{} missing", fsid, poolid, o);

            Ok(())
        }
    });

    try_join_all(xs).await?;

    Ok(())
}

async fn list_osts(poolid: i32, db_pool: &PgPool) -> Result<BTreeSet<i32>, Error> {
    let xs = sqlx::query!(
        "SELECT managedost_id FROM chroma_core_ostpool_osts WHERE ostpool_id = $1",
        poolid
    )
    .fetch(db_pool)
    .map_ok(|x| x.managedost_id)
    .try_collect()
    .await?;

    Ok(xs)
}

pub async fn diff(fsid: i32, poolid: i32, osts: &[String], db_pool: &PgPool) -> Result<(), Error> {
    let mut currentosts = list_osts(poolid, db_pool).await?;

    // Add New OSTs
    for ost in osts.iter() {
        if let Some(ostid) = ostid(fsid, &ost, db_pool).await? {
            if !currentosts.remove(&ostid) {
                sqlx::query!("INSERT INTO chroma_core_ostpool_osts (ostpool_id, managedost_id) VALUES ($1, $2)", poolid, ostid)
                .execute(db_pool)
                .await?;
            }
        }
    }

    // Remove OSTs not present
    let xs = currentosts.iter().map(|o| async move {
        sqlx::query!(
            "DELETE FROM chroma_core_ostpool_osts WHERE ostpool_id = $1 AND managedost_id = $2",
            poolid,
            o
        )
        .execute(db_pool)
        .await?;

        Ok(())
    });

    try_join_all(xs).await.map(drop)
}
