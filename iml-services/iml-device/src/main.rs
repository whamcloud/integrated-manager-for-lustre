// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::devices::Device;
use futures::{lock::Mutex, TryFutureExt, TryStreamExt};
use iml_device::{
    linux_plugin_transforms::{
        build_device_lookup, devtree2linuxoutput, get_shared_pools, populate_zpool, update_vgs,
        LinuxPluginData,
    },
    ImlDeviceError,
};
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::Fqdn;
use std::{
    collections::{BTreeMap, HashMap},
    sync::Arc,
};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::Filter;

type Cache = Arc<Mutex<HashMap<Fqdn, Device>>>;

#[tokio::main]
async fn main() -> Result<(), ImlDeviceError> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let addr = iml_manager_env::get_device_aggregator_addr();

    let cache = Arc::new(Mutex::new(HashMap::new()));
    let cache2 = Arc::clone(&cache);
    let cache = warp::any().map(move || Arc::clone(&cache));

    let mut s = consume_data("rust_agent_device_rx");

    while let Some((fqdn, device)) = s.try_next().await? {
        let mut cache = cache2.lock().await;

        cache.insert(fqdn, device);
    }

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

    Ok(())
}
