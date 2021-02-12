// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_change::GetChanges as _;
use emf_device::{
    build_device_index, create_cache, create_target_cache, filesystems, find_targets,
    update_client_mounts, update_devices, EmfDeviceError,
};
use emf_manager_env::get_pool_limit;
use emf_postgres::get_db_pool;
use emf_service_queue::spawn_service_consumer;
use emf_tracing::tracing;
use emf_wire_types::Fqdn;
use futures::{StreamExt, TryStreamExt};
use std::{
    collections::{BTreeSet, HashMap},
    iter::FromIterator,
    sync::Arc,
};

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), EmfDeviceError> {
    emf_tracing::init();

    let server_port = emf_manager_env::get_port("DEVICE_SERVICE_PORT");

    let db_port = emf_manager_env::get_port("DEVICE_SERVICE_PG_PORT");

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT), db_port).await?;

    sqlx::migrate!("../../migrations").run(&pool).await?;

    let cache = create_cache(&pool).await?;

    let cache2 = Arc::clone(&cache);

    tracing::info!("Server starting");

    let mut rx = spawn_service_consumer(server_port);

    let mut mount_cache = HashMap::new();

    let mut mgs_fs_cache = HashMap::new();

    while let Some((host, ((devices, mounts), mgs_fses))) = rx.next().await {
        update_devices(&pool, &host, &devices).await?;
        update_client_mounts(&pool, &host, &mounts).await?;

        let target_cache = create_target_cache(&pool).await?;

        let mut device_cache = cache2.lock().await;
        device_cache.insert(host.clone(), devices);
        mount_cache.insert(host.clone(), mounts);
        mgs_fs_cache.insert(host, mgs_fses);

        let index = build_device_index(&device_cache);

        let host_ids: HashMap<Fqdn, i32> = sqlx::query!("SELECT fqdn, id FROM host")
            .fetch(&pool)
            .map_ok(|x| (Fqdn(x.fqdn), x.id))
            .try_collect()
            .await?;

        tracing::debug!("mount_cache: {:?}", mount_cache);

        let targets = find_targets(
            &device_cache,
            &mount_cache,
            &host_ids,
            &index,
            &mgs_fs_cache,
        );

        tracing::debug!("targets: {:?}", targets);

        tracing::debug!("target_cache: {:?}", target_cache);

        let x = targets.get_changes(&target_cache);

        let xs = emf_device::build_updates(x);

        let x = xs.into_iter().fold(
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
            ),
            |mut acc, x| {
                let host_ids = BTreeSet::from_iter(x.host_ids)
                    .into_iter()
                    .map(|x: i32| x.to_string())
                    .collect::<Vec<_>>()
                    .join(",");

                acc.0.push(x.state);
                acc.1.push(x.name);
                acc.2.push(x.active_host_id);
                acc.3.push(host_ids);
                acc.4.push(x.filesystems.join(","));
                acc.5.push(x.uuid);
                acc.6.push(x.mount_path);
                acc.7.push(x.dev_path);
                acc.8.push(x.fs_type.map(|x| x.to_string()));
                acc
            },
        );

        tracing::debug!(?x);

        sqlx::query!(r#"INSERT INTO target
                        (state, name, active_host_id, host_ids, filesystems, uuid, mount_path, dev_path, fs_type)
                        SELECT state, name, active_host_id, string_to_array(host_ids, ',')::int[], string_to_array(filesystems, ',')::text[], uuid, mount_path, dev_path, fs_type
                        FROM UNNEST($1::text[], $2::text[], $3::int[], $4::text[], $5::text[], $6::text[], $7::text[], $8::text[], $9::fs_type[])
                        AS t(state, name, active_host_id, host_ids, filesystems, uuid, mount_path, dev_path, fs_type)
                        ON CONFLICT (name, uuid)
                            DO
                            UPDATE SET  state          = EXCLUDED.state,
                                        active_host_id = EXCLUDED.active_host_id,
                                        host_ids       = EXCLUDED.host_ids,
                                        filesystems    = EXCLUDED.filesystems,
                                        mount_path     = EXCLUDED.mount_path,
                                        dev_path       = EXCLUDED.dev_path,
                                        fs_type        = EXCLUDED.fs_type"#,
            &x.0,
            &x.1,
            &x.2 as &[Option<i32>],
            &x.3,
            &x.4,
            &x.5,
            &x.6 as &[Option<String>],
            &x.7 as &[Option<String>],
            &x.8 as &[Option<String>],
        )
        .execute(&pool)
        .await?;

        filesystems::learn(&pool).await?;
    }

    Ok(())
}
