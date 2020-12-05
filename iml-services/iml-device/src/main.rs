// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::{devices::Device, mount::Mount};
use futures::{TryFutureExt, TryStreamExt};
use im::HashSet;
use iml_change::GetChanges as _;
use iml_device::{
    build_device_index, client_mount_content_id, create_cache, create_target_cache, find_targets,
    get_mgs_filesystem_map, get_target_filesystem_map,
    linux_plugin_transforms::{
        build_device_lookup, devtree2linuxoutput, get_shared_pools, populate_zpool, update_vgs,
        LinuxPluginData,
    },
    update_client_mounts, update_devices, Cache, ImlDeviceError, TargetFsRecord,
};
use iml_influx::Client;
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db, get_pool_limit};
use iml_postgres::{get_db_pool, sqlx, PgPool};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::Fqdn;
use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    iter::FromIterator,
    sync::Arc,
};
use url::Url;
use warp::Filter;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), ImlDeviceError> {
    iml_tracing::init();

    let addr = iml_manager_env::get_device_aggregator_addr();

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;

    sqlx::migrate!("../../migrations").run(&pool).await?;

    let cache = create_cache(&pool).await?;

    let cache2 = Arc::clone(&cache);
    let cache = warp::any().map(move || Arc::clone(&cache));

    let get = warp::get().and(cache).and_then(|cache: Cache| {
        async move {
            let cache = cache.lock().await;

            let mut xs: BTreeMap<&Fqdn, _> = cache
                .iter()
                .map(|(k, v)| {
                    let mut out = LinuxPluginData::default();

                    devtree2linuxoutput(&v, None, &mut out);

                    (k, out)
                })
                .collect();

            let (path_index, cluster_pools): (HashMap<&Fqdn, _>, HashMap<&Fqdn, _>) = cache
                .iter()
                .map(|(k, v)| {
                    let mut path_to_mm = BTreeMap::new();
                    let mut pools = BTreeMap::new();

                    build_device_lookup(v, &mut path_to_mm, &mut pools);

                    ((k, path_to_mm), (k, pools))
                })
                .unzip();

            for (&h, x) in xs.iter_mut() {
                let path_to_mm = &path_index[h];
                let shared_pools = get_shared_pools(&h, path_to_mm, &cluster_pools);

                for (a, b) in shared_pools {
                    populate_zpool(a, b, x);
                }
            }

            let xs: BTreeMap<&Fqdn, LinuxPluginData> = update_vgs(xs, &path_index);

            Ok::<_, ImlDeviceError>(warp::reply::json(&xs))
        }
        .map_err(warp::reject::custom)
    });

    tracing::info!("Server starting");

    let server = warp::serve(get.with(warp::log("devices"))).run(addr);

    tokio::spawn(server);

    let rabbit_pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(rabbit_pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<(Device, HashSet<Mount>)>(&ch, "rust_agent_device_rx");

    let lustreclientmount_ct_id = client_mount_content_id(&pool).await?;

    let influx_url: String = format!("http://{}", get_influxdb_addr());

    let mut mount_cache = HashMap::new();

    let influx_client = Client::new(
        Url::parse(&influx_url).expect("Influx URL is invalid."),
        get_influxdb_metrics_db(),
    );

    while let Some((host, (devices, mounts))) = s.try_next().await? {
        update_devices(&pool, &host, &devices).await?;
        update_client_mounts(&pool, lustreclientmount_ct_id, &host, &mounts).await?;

        let target_cache = create_target_cache(&pool).await?;

        let mut device_cache = cache2.lock().await;
        device_cache.insert(host.clone(), devices);
        mount_cache.insert(host, mounts);

        let index = build_device_index(&device_cache);

        let host_ids: HashMap<Fqdn, i32> =
            sqlx::query!("SELECT fqdn, id FROM chroma_core_managedhost WHERE not_deleted = 't'",)
                .fetch(&pool)
                .map_ok(|x| (Fqdn(x.fqdn), x.id))
                .try_collect()
                .await?;

        let target_to_fs_map = get_target_filesystem_map(&influx_client).await?;
        let mgs_targets_to_fs_map = get_mgs_filesystem_map(&influx_client, &mount_cache).await?;
        let target_to_fs_map: TargetFsRecord = target_to_fs_map
            .into_iter()
            .chain(mgs_targets_to_fs_map)
            .collect();

        tracing::debug!("target_to_fs_map: {:?}", target_to_fs_map);

        tracing::debug!("mount_cache: {:?}", mount_cache);

        let targets = find_targets(
            &device_cache,
            &mount_cache,
            &host_ids,
            &index,
            &target_to_fs_map,
        );

        tracing::debug!("targets: {:?}", targets);

        tracing::debug!("target_cache: {:?}", target_cache);

        let x = targets.get_changes(&target_cache);

        let xs = iml_device::build_updates(x);

        let fses: std::collections::HashSet<String> = xs
            .iter()
            .flat_map(|x| x.filesystems.as_slice())
            .map(From::from)
            .collect();

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

        tracing::debug!("x: {:?}", x);

        sqlx::query!(r#"INSERT INTO target
                        (state, name, active_host_id, host_ids, filesystems, uuid, mount_path, dev_path, fs_type)
                        SELECT state, name, active_host_id, string_to_array(host_ids, ',')::int[], string_to_array(filesystems, ',')::text[], uuid, mount_path, dev_path, fs_type
                        FROM UNNEST($1::text[], $2::text[], $3::int[], $4::text[], $5::text[], $6::text[], $7::text[], $8::text[], $9::fs_type[])
                        AS t(state, name, active_host_id, host_ids, filesystems, uuid, mount_path, dev_path, fs_type)
                        ON CONFLICT (uuid)
                            DO
                            UPDATE SET  state          = EXCLUDED.state,
                                        name           = EXCLUDED.name,
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

        update_managed_targets(&pool, &x.0, &x.5).await?;

        update_managed_filesystems(&pool, Vec::from_iter(fses)).await?;
    }

    Ok(())
}

/// Update the state of any `ManagedTarget` records as we learn about state changes.
/// This should hopefully be removed in short order.
async fn update_managed_targets(
    pool: &PgPool,
    states: &Vec<String>,
    uuids: &Vec<String>,
) -> Result<(), ImlDeviceError> {
    sqlx::query!(
        r#"
        UPDATE chroma_core_managedtarget t
        SET state = updates.state
        FROM (
            SELECT state, uuid
            FROM UNNEST($1::text[], $2::text[])
            AS t(state, uuid)
        ) as updates
        WHERE t.uuid = updates.uuid
            AND t.not_deleted = 't'
    "#,
        states,
        uuids
    )
    .execute(pool)
    .await?;

    Ok(())
}

/// Update the state of any `ManagedFilesystem` records as we learn about state changes.
/// This should hopefully be removed in short order.
async fn update_managed_filesystems(
    pool: &PgPool,
    filesystems: Vec<String>,
) -> Result<(), ImlDeviceError> {
    let filesystems = sqlx::query!(
        r#"
        SELECT 
            mt.state,
            t.name,
            t.filesystems
            FROM chroma_core_managedtarget mt
            INNER JOIN target t
            ON t.uuid = mt.uuid
            WHERE mt.not_deleted = 't'
            AND $1::text[]  @> t.filesystems;
        "#,
        &filesystems
    )
    .fetch(pool)
    .try_fold(HashMap::new(), |mut acc, x| async {
        for fs in x.filesystems {
            let h = acc.entry(fs.to_string()).or_insert_with(|| HashMap::new());

            h.insert(x.name.to_string(), x.state.to_string());
        }

        Ok(acc)
    })
    .await?;

    let x = filesystems
        .into_iter()
        .fold((vec![], vec![]), |mut acc, (fsname, x)| {
            let is_stopped = x.values().all(|x| x == "unmounted");
            let is_unavailable = x
                .get(&format!("{}-MDT0000", fsname))
                .map(|x| x == "unmounted")
                .unwrap_or_default();

            let state = if is_stopped {
                "stopped"
            } else if is_unavailable {
                "unavailable"
            } else {
                "available"
            };

            acc.0.push(state.to_string());
            acc.1.push(fsname);

            acc
        });

    sqlx::query!(
        r#"
        UPDATE chroma_core_managedfilesystem
        SET 
            state = updates.state
        FROM (
                SELECT state, fsname
                FROM UNNEST($1::text[], $2::text[])
                AS t(state, fsname)
            ) AS updates
        WHERE 
        name = updates.fsname
        AND not_deleted = 't'
    "#,
        &x.0,
        &x.1,
    )
    .execute(pool)
    .await?;

    Ok(())
}
