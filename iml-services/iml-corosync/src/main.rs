// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryStreamExt;
use iml_manager_env::get_pool_limit;
use iml_postgres::{get_db_pool, sqlx, PgPool};
use iml_service_queue::service_queue::consume_data;
use iml_service_queue::service_queue::ImlServiceQueueError;
use iml_tracing::tracing;
use iml_wire_types::{
    high_availability::{Cluster, Node},
    Fqdn,
};
use thiserror::Error;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), ImlCorosyncError> {
    iml_tracing::init();

    let rabbit_pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(rabbit_pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<Cluster>(&ch, "rust_agent_corosync_rx");

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;

    sqlx::migrate!("../../migrations").run(&pool).await?;

    while let Some((fqdn, cluster)) = s.try_next().await? {
        let host_id = get_host_id_by_fqdn(&fqdn, &pool).await?;

        let host_id = match host_id {
            Some(id) => id,
            None => {
                tracing::warn!("Host '{}' is unknown, discarding incoming data", fqdn);

                continue;
            }
        };

        let (node_ids, node_names): (Vec<String>, Vec<String>) = cluster
            .nodes
            .iter()
            .map(|x| (x.id.to_string(), x.name.to_string()))
            .unzip();

        // Delete old rows
        sqlx::query!(
            r#"
            DELETE FROM corosync_node
            USING corosync_node_managed_host
            WHERE id = corosync_node_id AND name = corosync_node_name
            AND corosync_node_id != ALL($1)
            AND corosync_node_name != ALL($2)
            AND host_id = $3
        "#,
            &node_ids,
            &node_names,
            host_id
        )
        .execute(&pool)
        .await?;

        // Upsert the rest
        upsert_cluster_nodes(cluster.nodes, &pool).await?;

        sqlx::query!(
            r#"
            INSERT INTO corosync_node_managed_host (host_id, corosync_node_id, corosync_node_name)
            SELECT $1, corosync_node_id, corosync_node_name FROM UNNEST($2::text[], $3::text[])
            AS t(corosync_node_id, corosync_node_name)
            ON CONFLICT (host_id, corosync_node_id, corosync_node_name)
            DO NOTHING
            "#,
            host_id,
            &node_ids,
            &node_names
        )
        .execute(&pool)
        .await?;
    }

    Ok(())
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

async fn get_host_id_by_fqdn(fqdn: &Fqdn, pool: &PgPool) -> Result<Option<i32>, ImlCorosyncError> {
    let id = sqlx::query!(
        "select id from chroma_core_managedhost where fqdn = $1 and not_deleted = 't'",
        fqdn.to_string()
    )
    .fetch_optional(pool)
    .await?
    .map(|x| x.id);

    Ok(id)
}

async fn upsert_cluster_nodes(nodes: Vec<Node>, pool: &PgPool) -> Result<(), ImlCorosyncError> {
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
            vec![],
        ),
        |mut acc, x| {
            acc.0.push(x.name);
            acc.1.push(x.id);
            acc.2.push(x.online);
            acc.3.push(x.standby);
            acc.4.push(x.standby_onfail);
            acc.5.push(x.maintenance);
            acc.6.push(x.pending);
            acc.7.push(x.unclean);
            acc.8.push(x.shutdown);
            acc.9.push(x.expected_up);
            acc.10.push(x.is_dc);
            acc.11.push(x.resources_running as i32);
            acc.12.push(x.r#type.to_string());

            acc
        },
    );

    sqlx::query!(
        r#"
            INSERT INTO corosync_node (
                name,
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
            SELECT
                name,
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
            FROM UNNEST(
                $1::text[],
                $2::text[],
                $3::bool[],
                $4::bool[],
                $5::bool[],
                $6::bool[],
                $7::bool[],
                $8::bool[],
                $9::bool[],
                $10::bool[],
                $11::bool[],
                $12::int[],
                $13::text[]
            )
            AS t(
                name,
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
            ON CONFLICT (id, name) DO UPDATE
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
        &x.12,
    )
    .execute(pool)
    .await?;

    Ok(())
}
