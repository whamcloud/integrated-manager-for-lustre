// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_postgres::{sqlx, PgPool};
use iml_service_queue::service_queue::ImlServiceQueueError;
use iml_wire_types::high_availability::{Ban, Node, Resource};
use std::{collections::HashMap, fmt};
use thiserror::Error;

#[derive(Debug, Clone, Ord, PartialOrd, Eq, PartialEq, sqlx::Type)]
#[sqlx(rename = "corosync_node_key")]
pub struct CorosyncNodeKey {
    pub id: String,
    pub name: String,
}

impl fmt::Display for CorosyncNodeKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, r#"("{}","{}")"#, self.id, self.name)
    }
}

impl From<(String, String)> for CorosyncNodeKey {
    fn from((id, name): (String, String)) -> Self {
        Self { id, name }
    }
}

#[derive(Error, Debug)]
pub enum ImlCorosyncError {
    #[error(transparent)]
    ImlRabbitError(#[from] iml_rabbit::ImlRabbitError),
    #[error(transparent)]
    ImlServiceQueueError(#[from] ImlServiceQueueError),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
    #[error(transparent)]
    SqlxCoreError(#[from] sqlx::Error),
    #[error(transparent)]
    SqlxMigrateError(#[from] sqlx::migrate::MigrateError),
}

pub async fn delete_cluster(
    host_id: i32,
    xs: &[String],
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    sqlx::query!(
        r#"
            DELETE FROM corosync_cluster
            USING corosync_node_managed_host
            WHERE host_id = $1
            AND cluster_id = id
            AND corosync_nodes != $2::corosync_node_key[]
        "#,
        host_id,
        xs as &[String]
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn upsert_corosync_cluster(xs: &[String], pool: &PgPool) -> Result<(), ImlCorosyncError> {
    sqlx::query!(
        r#"
                INSERT INTO corosync_cluster (corosync_nodes)
                VALUES ($1::corosync_node_key[])
                ON CONFLICT (corosync_nodes) DO NOTHING
            "#,
        xs as &[String]
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn fetch_corosync_cluster_by_nodes(
    xs: &[String],
    pool: &PgPool,
) -> Result<i32, ImlCorosyncError> {
    let cluster_id = sqlx::query!(
        r#"
            SELECT id FROM corosync_cluster
            WHERE corosync_nodes = $1::corosync_node_key[]
        "#,
        &xs as &[String]
    )
    .fetch_one(pool)
    .await?
    .id;

    Ok(cluster_id)
}

pub async fn delete_corosync_resource_bans(
    host_id: i32,
    ban_ids: &[String],
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    sqlx::query!(
        r#"
            DELETE FROM corosync_resource_bans
            USING corosync_node_managed_host
            WHERE host_id = $1
            AND node = (corosync_node_id).name
            AND id != ALL($2)
            "#,
        host_id,
        &ban_ids
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn delete_nodes(
    host_id: i32,
    xs: &[String],
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    sqlx::query!(
        r#"
            DELETE FROM corosync_node
            USING corosync_node_managed_host
            WHERE id = corosync_node_id
            AND host_id = $1
            AND corosync_node_id != ALL($2::corosync_node_key[])
        "#,
        host_id,
        &xs as &[String]
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn delete_target_resources(
    host_id: i32,
    xs: &[String],
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    sqlx::query!(
        r#"
            DELETE FROM corosync_resource
            USING corosync_resource_managed_host
            WHERE id = corosync_resource_id
            AND corosync_resource_id != ALL($1)
            AND host_id = $2
        "#,
        &xs,
        host_id
    )
    .execute(pool)
    .await?;

    sqlx::query!(
        r#"
            DELETE FROM corosync_resource_managed_host
            WHERE corosync_resource_id != ALL($1)
            AND host_id = $2
        "#,
        &xs,
        host_id
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn upsert_resource_bans(
    cluster_id: i32,
    bans: Vec<Ban>,
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    let x = bans
        .into_iter()
        .fold((vec![], vec![], vec![], vec![], vec![]), |mut acc, x| {
            acc.0.push(x.id);
            acc.1.push(x.resource);
            acc.2.push(x.node);
            acc.3.push(x.weight);
            acc.4.push(x.master_only);

            acc
        });

    sqlx::query!(
        r#"
            INSERT INTO corosync_resource_bans (id, cluster_id, resource, node, weight, master_only)
            SELECT
                id,
                $6,
                resource,
                node,
                weight,
                master_only
            FROM UNNEST(
                $1::text[],
                $2::text[],
                $3::text[],
                $4::int[],
                $5::bool[]
            )
            AS t(
                id,
                resource,
                node,
                weight,
                master_only
            )
            ON CONFLICT (id, cluster_id, resource, node) DO UPDATE
            SET
                weight = excluded.weight,
                master_only = excluded.master_only
        "#,
        &x.0,
        &x.1,
        &x.2,
        &x.3,
        &x.4,
        cluster_id
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn upsert_target_resources(
    resources: Vec<Resource>,
    mounts: HashMap<String, String>,
    cluster_id: i32,
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    let x = resources.into_iter().fold(
        (
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
        ),
        |mut acc, x| {
            let m: Option<&str> = mounts.get(&x.id).map(|x| x.as_str());

            let active_node = match (x.active_node_id, x.active_node_name) {
                (Some(x), Some(y)) => Some(CorosyncNodeKey::from((x, y)).to_string()),
                _ => None,
            };

            acc.0.push(x.id);
            acc.1.push(x.resource_agent);
            acc.2.push(x.role);
            acc.3.push(x.active);
            acc.4.push(x.orphaned);
            acc.5.push(x.managed);
            acc.6.push(x.failed);
            acc.7.push(x.failure_ignored);
            acc.8.push(x.nodes_running_on as i32);
            acc.9.push(active_node);
            acc.10.push(m);

            acc
        },
    );

    sqlx::query!(
        r#"
        INSERT INTO corosync_resource (
            id,
            cluster_id,
            resource_agent,
            role,
            active,
            orphaned,
            managed,
            failed,
            failure_ignored,
            nodes_running_on,
            active_node,
            mount_point
        )
        SELECT
            id,
            $12,
            resource_agent,
            role,
            active,
            orphaned,
            managed,
            failed,
            failure_ignored,
            nodes_running_on,
            active_node::corosync_node_key,
            mount_point
        FROM UNNEST(
                $1::text[],
                $2::text[],
                $3::text[],
                $4::bool[],
                $5::bool[],
                $6::bool[],
                $7::bool[],
                $8::bool[],
                $9::int[],
                $10::text[],
                $11::text[]
            )
            AS t(
            id,
            resource_agent,
            role,
            active,
            orphaned,
            managed,
            failed,
            failure_ignored,
            nodes_running_on,
            active_node,
            mount_point
            )
            ON CONFLICT (id, cluster_id) DO UPDATE
            SET
                resource_agent = excluded.resource_agent,
                role = excluded.role,
                active = excluded.active,
                orphaned = excluded.orphaned,
                managed = excluded.managed,
                failed = excluded.failed,
                failure_ignored = excluded.failure_ignored,
                nodes_running_on = excluded.nodes_running_on,
                active_node = excluded.active_node,
                mount_point = excluded.mount_point
    "#,
        &x.0,
        &x.1,
        &x.2,
        &x.3,
        &x.4,
        &x.5,
        &x.6,
        &x.7,
        &x.8,
        &x.9 as &[Option<String>],
        &x.10 as &Vec<Option<&str>>,
        cluster_id,
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn upsert_cluster_nodes(
    nodes: Vec<Node>,
    cluster_id: i32,
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    let x = nodes.into_iter().fold(
        (
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
        ),
        |mut acc, x| {
            acc.0
                .push(CorosyncNodeKey::from((x.id, x.name)).to_string());
            acc.1.push(x.online);
            acc.2.push(x.standby);
            acc.3.push(x.standby_onfail);
            acc.4.push(x.maintenance);
            acc.5.push(x.pending);
            acc.6.push(x.unclean);
            acc.7.push(x.shutdown);
            acc.8.push(x.expected_up);
            acc.9.push(x.is_dc);
            acc.10.push(x.resources_running as i32);
            acc.11.push(x.r#type.to_string());

            acc
        },
    );

    sqlx::query!(
        r#"
            INSERT INTO corosync_node (
                id,
                cluster_id,
                online,
                standby,
                standby_onfail,
                maintenance,
                pending,
                unclean,
                shutdown,
                expected_up,
                is_dc,
                resources_running,
                type
            )
            SELECT
                id::corosync_node_key,
                $13,
                online,
                standby,
                standby_onfail,
                maintenance,
                pending,
                unclean,
                shutdown,
                expected_up,
                is_dc,
                resources_running,
                type
            FROM UNNEST(
                $1::text[],
                $2::bool[],
                $3::bool[],
                $4::bool[],
                $5::bool[],
                $6::bool[],
                $7::bool[],
                $8::bool[],
                $9::bool[],
                $10::bool[],
                $11::int[],
                $12::text[]
            )
            AS t(
                id,
                online,
                standby,
                standby_onfail,
                maintenance,
                pending,
                unclean,
                shutdown,
                expected_up,
                is_dc,
                resources_running,
                type
            )
            ON CONFLICT (id, cluster_id) DO UPDATE
            SET
                online = excluded.online,
                standby = excluded.standby,
                standby_onfail = excluded.standby_onfail,
                maintenance = excluded.maintenance,
                pending = excluded.pending,
                unclean = excluded.unclean,
                shutdown = excluded.shutdown,
                expected_up = excluded.expected_up,
                is_dc = excluded.is_dc,
                resources_running = excluded.resources_running,
                type = excluded.type
        "#,
        &x.0,
        &x.1,
        &x.2,
        &x.3,
        &x.4,
        &x.5,
        &x.6,
        &x.7,
        &x.8,
        &x.9,
        &x.10,
        &x.11,
        cluster_id
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn upsert_node_managed_host(
    host_id: i32,
    cluster_id: i32,
    node_key: CorosyncNodeKey,
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    sqlx::query!(
        r#"
            INSERT INTO corosync_node_managed_host (host_id, cluster_id, corosync_node_id)
            VALUES($1, $2, $3::corosync_node_key)
            ON CONFLICT (host_id, corosync_node_id, cluster_id)
            DO NOTHING
            "#,
        host_id,
        cluster_id,
        node_key.to_string() as String
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn upsert_target_resource_managed_host(
    host_id: i32,
    cluster_id: i32,
    xs: &[String],
    pool: &PgPool,
) -> Result<(), ImlCorosyncError> {
    sqlx::query!(
        r#"
                INSERT INTO corosync_resource_managed_host (host_id, cluster_id, corosync_resource_id)
                SELECT $1, $2, corosync_resource_id FROM UNNEST($3::text[]) as corosync_resource_id
                ON CONFLICT (host_id, corosync_resource_id, cluster_id)
                DO NOTHING
            "#,
        host_id,
        cluster_id,
        xs
    )
    .execute(pool)
    .await?;

    Ok(())
}
