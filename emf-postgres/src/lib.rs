// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod alert;

use emf_wire_types::{BannedTargetResource, Fqdn, TargetResource};
use futures::{future, TryStreamExt};
use sqlx::postgres::{PgConnectOptions, PgPoolOptions};
pub use sqlx::{self, postgres::PgPool};
use std::collections::HashSet;

pub async fn get_db_pool(pool_size: u32, port: u16) -> Result<PgPool, sqlx::Error> {
    let mut opts = PgConnectOptions::default()
        .username(&emf_manager_env::get_pg_user())
        .host("127.0.0.1")
        .port(port);

    opts = if let Some(x) = emf_manager_env::get_pg_name() {
        opts.database(&x)
    } else {
        opts
    };

    opts = if let Some(x) = emf_manager_env::get_pg_password() {
        opts.password(&x)
    } else {
        opts
    };

    let x = PgPoolOptions::new()
        .max_connections(pool_size)
        .connect_with(opts)
        .await?;

    Ok(x)
}

pub async fn fqdn_by_host_id(pool: &PgPool, id: i32) -> Result<String, sqlx::Error> {
    let fqdn = sqlx::query!(r#"SELECT fqdn FROM host WHERE id=$1"#, id)
        .fetch_one(pool)
        .await?
        .fqdn;

    Ok(fqdn)
}

pub async fn host_id_by_fqdn(fqdn: &Fqdn, pool: &PgPool) -> Result<Option<i32>, sqlx::Error> {
    let id = sqlx::query!("select id from host where fqdn = $1", fqdn.to_string())
        .fetch_optional(pool)
        .await?
        .map(|x| x.id);

    Ok(id)
}

pub async fn active_mgs_host_fqdn(
    fsname: &str,
    pool: &PgPool,
) -> Result<Option<String>, sqlx::Error> {
    let fsnames = &[fsname.into()][..];
    let maybe_active_mgs_host_id = sqlx::query!(
        r#"
            SELECT active_host_id from target WHERE filesystems @> $1 and name='MGS'
        "#,
        fsnames
    )
    .fetch_optional(pool)
    .await?
    .and_then(|x| x.active_host_id);

    tracing::trace!("Maybe active MGS host id: {:?}", maybe_active_mgs_host_id);

    if let Some(active_mgs_host_id) = maybe_active_mgs_host_id {
        let active_mgs_host_fqdn = fqdn_by_host_id(pool, active_mgs_host_id).await?;

        Ok(Some(active_mgs_host_fqdn))
    } else {
        Ok(None)
    }
}

pub async fn get_fs_target_resources(
    pool: &PgPool,
    fs_name: Option<String>,
) -> Result<Vec<TargetResource>, sqlx::Error> {
    let banned_resources = get_banned_targets(pool).await?;

    let xs = sqlx::query!(r#"
            SELECT
                rh.cluster_id,
                r.name as resource_id,
                t.id as target_id,
                t.name,
                t.mount_path,
                t.filesystems,
                t.uuid,
                t.state,
                array_agg(DISTINCT rh.host_id) AS "cluster_hosts!"
            FROM target t
            INNER JOIN corosync_resource r ON r.mount_point = t.mount_path
            INNER JOIN corosync_resource_host rh ON rh.corosync_resource_id = r.name AND rh.host_id = ANY(t.host_ids)
            WHERE CARDINALITY(t.filesystems) > 0
            GROUP BY rh.cluster_id, t.name, r.name, t.mount_path, t.uuid, t.filesystems, t.state, t.id
        "#)
            .fetch(pool)
            .try_filter(|x| {
                let x = match fs_name.as_ref() {
                    None => true,
                    Some(fs) => (&x.filesystems).contains(fs)
                };

                future::ready(x)
            })
            .map_ok(|mut x| {
                let xs:HashSet<_> = banned_resources
                    .iter()
                    .filter(|y| {
                        y.cluster_id == x.cluster_id && y.resource == x.resource_id &&  x.mount_path == y.mount_point
                    })
                    .map(|y| y.host_id)
                    .collect();

                x.cluster_hosts.retain(|id| !xs.contains(id));

                x
            })
            .map_ok(|x| {
                TargetResource {
                    cluster_id: x.cluster_id,
                    fs_names: x.filesystems,
                    uuid: x.uuid,
                    name: x.name,
                    resource_id: x.resource_id,
                    target_id: x.target_id,
                    state: x.state,
                    cluster_hosts: x.cluster_hosts
                }
            }).try_collect()
            .await?;

    Ok(xs)
}

pub async fn get_banned_targets(pool: &PgPool) -> Result<Vec<BannedTargetResource>, sqlx::Error> {
    let xs = sqlx::query_as!(
        BannedTargetResource,
        r#"
            SELECT b.resource as "resource!", b.cluster_id as "cluster_id!",
                   nh.host_id as "host_id!", t.mount_point
            FROM corosync_resource_bans b
            INNER JOIN corosync_node_host nh ON (nh.corosync_node_id).name = b.node
            AND nh.cluster_id = b.cluster_id
            INNER JOIN corosync_resource t ON t.name = b.resource AND b.cluster_id = t.cluster_id
            WHERE t.mount_point is not NULL
        "#
    )
    .fetch(pool)
    .try_collect()
    .await?;

    Ok(xs)
}

#[cfg(feature = "test")]
use dotenv::dotenv;

/// Setup for a test run. This fn hands out a pool
/// with a single connection and starts a transaction for it.
/// The transaction is rolled back when the connection closes
/// so nothing is written to the database.
#[cfg(feature = "test")]
pub async fn test_setup() -> Result<PgPool, sqlx::Error> {
    dotenv().ok();

    let pool = get_db_pool(1, 5432).await?;

    sqlx::query("BEGIN TRANSACTION").execute(&pool).await?;

    Ok(pool)
}
