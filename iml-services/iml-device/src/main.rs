// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::{devices::Device, mount::Mount};
use futures::{TryFutureExt, TryStreamExt};
use im::HashSet;
use iml_device::{
    client_mount_content_id, create_cache,
    linux_plugin_transforms::{
        build_device_lookup, devtree2linuxoutput, get_shared_pools, populate_zpool, update_vgs,
        LinuxPluginData,
    },
    update_client_mounts, update_devices, Cache, ImlDeviceError,
};
use iml_manager_env::get_pool_limit;
use iml_postgres::get_db_pool;
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::Fqdn;
use std::{
    collections::{BTreeMap, HashMap},
    sync::Arc,
};
use warp::Filter;

// Default pool limit if not overwridden by POOL_LIMIT
const POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), ImlDeviceError> {
    iml_tracing::init();

    let addr = iml_manager_env::get_device_aggregator_addr();

    let pool = get_db_pool(get_pool_limit().unwrap_or(POOL_LIMIT)).await?;

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

    while let Some((host, (devices, mounts))) = s.try_next().await? {
        update_devices(&pool, &host, &devices).await?;
        update_client_mounts(&pool, lustreclientmount_ct_id, &host, &mounts).await?;

        let mut cache = cache2.lock().await;
        cache.insert(host, devices);
    }

    Ok(())
}
