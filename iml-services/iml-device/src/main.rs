// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::prelude::*;
use device_types::devices::Device;
use diesel::{self, pg::upsert::excluded, prelude::*};
use futures::{lock::Mutex, TryFutureExt, TryStreamExt};

use iml_device::{
    linux_plugin_transforms::{
        build_device_lookup, devtree2linuxoutput, get_shared_pools, populate_zpool, update_vgs,
        LinuxPluginData,
    },
    virtual_device::{get_other_devices, save_devices, update_virtual_devices},
    ImlDeviceError,
};
use iml_orm::{
    models::{ChromaCoreDevice, NewChromaCoreDevice},
    schema::chroma_core_device::{devices, fqdn, table},
    tokio_diesel::*,
    DbPool,
};
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::Fqdn;
use std::{
    collections::{BTreeMap, HashMap},
    sync::Arc,
};
use warp::Filter;

type Cache = Arc<Mutex<HashMap<Fqdn, Device>>>;

async fn create_cache(pool: &DbPool) -> Result<Cache, ImlDeviceError> {
    let data: HashMap<Fqdn, Device> = table
        .load_async(&pool)
        .await?
        .into_iter()
        .map(
            |x: ChromaCoreDevice| -> Result<(Fqdn, Device), ImlDeviceError> {
                let d = serde_json::from_value(x.devices)?;

                Ok((Fqdn(x.fqdn), d))
            },
        )
        .collect::<Result<_, _>>()?;

    Ok(Arc::new(Mutex::new(data)))
}

#[tokio::main]
async fn main() -> Result<(), ImlDeviceError> {
    iml_tracing::init();

    let addr = iml_manager_env::get_device_aggregator_addr();

    let pool = iml_orm::pool()?;

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

    let mut s = consume_data::<Device>("rust_agent_device_rx");

    let mut i = 0usize;
    // You may observe spurious updates.
    // This means that, when a single device is mounted, updated device tree may come in here several times from a single host.
    // This is due to two reasons:
    // 1. The swap-emitter service on the storage node fires once per minute, so there will be an update of the tree at agent side at that interval no matter what.
    // 2. When device-scanner starts it does not fill any of the state, so there will always be data sent for the first update (state #2 below).
    //
    // Device scanner switches its (previous, current) states like this:
    // #       1               2                  3
    // state   (None, None) -> (None, initial) -> (initial, initial)
    // A change is observed when agent is polled while it's in the middle state, and it will be in that state for a minute until swap-emitter fires.
    //
    // In summary, you can observe up to a minute of incoming updates, with a period of roughly 10 seconds.
    // The period is usually a bit longer due to overhead. So a max of 5 updates has been observed in practice.
    //
    while let Some((f, d)) = s.try_next().await? {
        let begin: DateTime<Local> = Local::now();
        tracing::info!("Iteration {}: begin: {}", i, begin);

        let mut cache = cache2.lock().await;
        cache.insert(f.clone(), d.clone());

        assert!(
            match d {
                Device::Root(_) => true,
                _ => false,
            },
            "The top device has to be Root"
        );

        let mut all_devices = get_other_devices(&f, &pool).await;

        all_devices.push((f, d));

        let updated_devices = update_virtual_devices(all_devices);

        save_devices(updated_devices, &pool).await;

        let end: DateTime<Local> = Local::now();

        tracing::info!(
            "Iteration {}: end: {}, duration: {:3} ms",
            i,
            end,
            (end - begin).num_milliseconds()
        );

        i = i.wrapping_add(1);
    }

    Ok(())
}
