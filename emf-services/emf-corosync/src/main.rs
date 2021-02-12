// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_corosync::{
    delete_cluster, delete_corosync_resource_bans, delete_nodes, delete_target_resources,
    fetch_corosync_cluster_by_nodes, update_chroma_ticket, upsert_cluster_nodes,
    upsert_corosync_cluster, upsert_node_managed_host, upsert_resource_bans,
    upsert_target_resource_managed_host, upsert_target_resources, CorosyncNodeKey,
    EmfCorosyncError,
};
use emf_manager_env::get_pool_limit;
use emf_postgres::{get_db_pool, host_id_by_fqdn};
use emf_service_queue::spawn_service_consumer;
use emf_tracing::tracing;
use emf_wire_types::high_availability::Cluster;
use futures::StreamExt;
use std::collections::BTreeSet;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), EmfCorosyncError> {
    emf_tracing::init();

    let pool = get_db_pool(
        get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT),
        emf_manager_env::get_port("COROSYNC_SERVICE_PG_PORT"),
    )
    .await?;

    sqlx::migrate!("../../migrations").run(&pool).await?;

    let mut rx = spawn_service_consumer::<(String, Cluster)>(emf_manager_env::get_port(
        "COROSYNC_SERVICE_PORT",
    ));

    while let Some((fqdn, (local_node_id, cluster))) = rx.next().await {
        let host_id = host_id_by_fqdn(&fqdn, &pool).await?;

        let host_id = match host_id {
            Some(id) => id,
            None => {
                tracing::warn!("Host '{}' is unknown, discarding incoming data", fqdn);

                continue;
            }
        };

        let node_keys: BTreeSet<CorosyncNodeKey> = cluster
            .nodes
            .iter()
            .map(|x| (x.id.to_string(), x.name.to_string()).into())
            .collect();

        let local_node = cluster.nodes.iter().find(|x| x.id == local_node_id);

        let local_node_key: CorosyncNodeKey = match local_node {
            Some(x) => (x.id.to_string(), x.name.to_string()).into(),
            None => {
                tracing::warn!(
                    "Could not resolve node id {} to a local node, discarding incoming data",
                    local_node_id
                );

                continue;
            }
        };

        let node_keys_db: Vec<String> = node_keys.iter().map(CorosyncNodeKey::to_string).collect();

        let resource_ids: Vec<String> =
            cluster.resources.iter().map(|x| x.id.to_string()).collect();

        let ban_ids: Vec<String> = cluster.bans.iter().map(|x| x.id.to_string()).collect();

        upsert_corosync_cluster(&node_keys_db, &pool).await?;

        let cluster_id = fetch_corosync_cluster_by_nodes(&node_keys_db, &pool).await?;

        // Delete old rows
        delete_cluster(host_id, &node_keys_db, &pool).await?;

        delete_corosync_resource_bans(host_id, &ban_ids, &pool).await?;

        delete_nodes(host_id, &node_keys_db, &pool).await?;

        delete_target_resources(host_id, &resource_ids, &pool).await?;

        // Upsert the rest
        upsert_cluster_nodes(cluster.nodes, cluster_id, &pool).await?;

        update_chroma_ticket(&cluster.resources, cluster_id, &pool).await?;

        upsert_target_resources(
            cluster.resources,
            cluster.resource_mounts,
            cluster_id,
            &pool,
        )
        .await?;

        upsert_resource_bans(cluster_id, cluster.bans, &pool).await?;

        upsert_node_managed_host(host_id, cluster_id, local_node_key, &pool).await?;

        upsert_target_resource_managed_host(host_id, cluster_id, &resource_ids, &pool).await?;
    }

    Ok(())
}
