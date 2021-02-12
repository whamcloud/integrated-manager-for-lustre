// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::Error;
use emf_tracing::tracing;
use emf_wire_types::OstPool;
use futures::{future::try_join_all, TryStreamExt};
use sqlx::postgres::PgPool;
use std::collections::BTreeSet;

/// Assume that if there is a single filesystem with a given name,
/// that it's the correct one
pub async fn fsid(fsname: &str, db_pool: &PgPool) -> Result<i32, Error> {
    let x = sqlx::query!("SELECT id FROM filesystem WHERE name=$1", fsname)
        .fetch_one(db_pool)
        .await?
        .id;

    Ok(x)
}

pub async fn poolid(fsid: i32, pn: &str, db_pool: &PgPool) -> Result<Option<i32>, Error> {
    let x = sqlx::query!(
        "SELECT id FROM ostpool WHERE name=$1 AND filesystem_id=$2",
        pn,
        fsid
    )
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
    let bs = sqlx::query!("SELECT name FROM ostpool WHERE filesystem_id=$1", fsid)
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

async fn ostid(fsname: &str, ost: &str, db_pool: &PgPool) -> Result<Option<i32>, Error> {
    let x = sqlx::query!(
        r#"
            SELECT t.id
            FROM target AS t
            WHERE $1 = ANY(t.filesystems)
            AND name = $2"#,
        &fsname,
        &ost
    )
    .fetch_optional(db_pool)
    .await?
    .map(|x| x.id);

    Ok(x)
}

pub async fn create(fsid: i32, pn: &str, db_pool: &PgPool) -> Result<i32, Error> {
    let x = sqlx::query!(
        "INSERT INTO ostpool (name, filesystem_id) VALUES ($1, $2) RETURNING id",
        pn,
        fsid
    )
    .fetch_one(db_pool)
    .await?
    .id;

    Ok(x)
}

pub async fn delete(fsid: i32, pn: &str, db_pool: &PgPool) -> Result<(), Error> {
    sqlx::query!(
        "DELETE FROM ostpool WHERE filesystem_id = $1 AND name = $2",
        fsid,
        pn
    )
    .execute(db_pool)
    .await?;

    Ok(())
}

pub async fn grow(
    fsname: &str,
    poolid: i32,
    osts: &[String],
    db_pool: &PgPool,
) -> Result<(), Error> {
    let xs = osts.iter().map(|o| async move {
        if let Some(ostid) = ostid(fsname, &o, db_pool).await? {
            let exists = sqlx::query!(
                "SELECT id FROM ostpool_osts WHERE ostpool_id = $1 AND ost_id = $2",
                poolid,
                ostid
            )
            .fetch_optional(db_pool)
            .await?
            .is_some();

            if exists {
                tracing::debug!("Growing ({}).({}): ost:{}({})", fsname, poolid, o, ostid);

                sqlx::query!(
                    "INSERT INTO ostpool_osts (ostpool_id, ost_id) VALUES ($1, $2)",
                    poolid,
                    ostid
                )
                .execute(db_pool)
                .await?;

                Ok::<_, Error>(())
            } else {
                tracing::debug!("Grow ({}).({}): ost:{} already exists", fsname, poolid, o);

                Ok(())
            }
        } else {
            tracing::warn!("Failed Grow ({}).({}): ost:{} missing", fsname, poolid, o);

            Ok(())
        }
    });

    try_join_all(xs).await?;

    Ok(())
}

pub async fn shrink(
    fsname: &str,
    poolid: i32,
    osts: &[String],
    db_pool: &PgPool,
) -> Result<(), Error> {
    let xs = osts.iter().map(|o| async move {
        if let Some(ostid) = ostid(fsname, &o, db_pool).await? {
            tracing::debug!("Shrinking ({}).({}): ost:{}({})", fsname, poolid, o, ostid);

            sqlx::query!(
                "DELETE FROM ostpool_osts WHERE ostpool_id = $1 AND ost_id = $2",
                poolid,
                ostid
            )
            .execute(db_pool)
            .await?;

            Ok::<_, Error>(())
        } else {
            tracing::warn!("Failed Shrink ({}).({}): ost:{} missing", fsname, poolid, o);

            Ok(())
        }
    });

    try_join_all(xs).await?;

    Ok(())
}

async fn list_osts(poolid: i32, db_pool: &PgPool) -> Result<BTreeSet<i32>, Error> {
    let xs = sqlx::query!(
        "SELECT ost_id FROM ostpool_osts WHERE ostpool_id = $1",
        poolid
    )
    .fetch(db_pool)
    .map_ok(|x| x.ost_id)
    .try_collect()
    .await?;

    Ok(xs)
}

pub async fn diff(
    fsname: &str,
    poolid: i32,
    osts: &[String],
    db_pool: &PgPool,
) -> Result<(), Error> {
    let mut currentosts = list_osts(poolid, db_pool).await?;

    // Add New OSTs
    for ost in osts.iter() {
        if let Some(ostid) = ostid(fsname, &ost, db_pool).await? {
            if !currentosts.remove(&ostid) {
                sqlx::query!(
                    "INSERT INTO ostpool_osts (ostpool_id, ost_id) VALUES ($1, $2)",
                    poolid,
                    ostid
                )
                .execute(db_pool)
                .await?;
            }
        }
    }

    // Remove OSTs not present
    let xs = currentosts.iter().map(|o| async move {
        sqlx::query!(
            "DELETE FROM ostpool_osts WHERE ostpool_id = $1 AND ost_id = $2",
            poolid,
            o
        )
        .execute(db_pool)
        .await?;

        Ok(())
    });

    try_join_all(xs).await.map(drop)
}
