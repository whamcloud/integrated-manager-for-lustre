// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::devices::Device;
use diesel::{self, pg::upsert::excluded, prelude::*};
use futures::{lock::Mutex, TryFutureExt, TryStreamExt};
use iml_device::{
    linux_plugin_transforms::{
        build_device_lookup, devtree2linuxoutput, get_shared_pools, populate_zpool, update_vgs,
        LinuxPluginData,
    },
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
    fs::File,
    io::Write,
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
    while let Some((f, d)) = s.try_next().await? {
        let mut cache = cache2.lock().await;

        assert!(
            match d {
                Device::Root(_) => true,
                _ => false,
            },
            "The top device has to be Root"
        );

        println!("Host: {}", f);

        let mut ff = File::create(format!("/tmp/device{}", i)).unwrap();
        ff.write_all(serde_json::to_string_pretty(&d).unwrap().as_bytes())
            .unwrap();
        let mut parents = vec![];
        walk(&d, 0, None, &mut parents);
        let mut ff = File::create(format!("/tmp/parents{}", i)).unwrap();
        ff.write_all(serde_json::to_string_pretty(&parents).unwrap().as_bytes())
            .unwrap();

        cache.insert(f.clone(), d.clone());

        let device_to_insert = NewChromaCoreDevice {
            fqdn: f.to_string(),
            devices: serde_json::to_value(d).expect("Could not convert incoming Devices to JSON."),
        };

        let new_device = diesel::insert_into(table)
            .values(device_to_insert)
            .on_conflict(fqdn)
            .do_update()
            .set(devices.eq(excluded(devices)))
            .get_result_async::<ChromaCoreDevice>(&pool)
            .await
            .expect("Error saving new device");

        tracing::info!("Inserted device from host {}", new_device.fqdn);
        tracing::trace!("Inserted device {:?}", new_device);

        i += 1;
    }

    Ok(())
}

fn is_virtual(d: &Device) -> bool {
    match d {
        Device::Dataset(_)
        | Device::LogicalVolume(_)
        | Device::MdRaid(_)
        | Device::VolumeGroup(_)
        | Device::Zpool(_) => true,
        _ => false,
    }
}

fn walk<'d>(
    d: &'d Device,
    level: usize,
    parent: Option<&'d Device>,
    mut parents: &mut Vec<&'d Device>,
) {
    if is_virtual(d) {
        parents.push(
            parent.expect("Tried to push to parents the parent of the Root, which doesn't exist"),
        );
    } else {
        match d {
            Device::Root(dd) => {
                for c in dd.children.iter() {
                    walk(c, level + 1, Some(d), &mut parents);
                }
            }
            Device::ScsiDevice(dd) => {
                for c in dd.children.iter() {
                    walk(c, level + 1, Some(d), &mut parents);
                }
            }
            Device::Partition(dd) => {
                for c in dd.children.iter() {
                    walk(c, level + 1, Some(d), &mut parents);
                }
            }
            Device::Mpath(dd) => {
                for c in dd.children.iter() {
                    walk(c, level + 1, Some(d), &mut parents);
                }
            }
            _ => unreachable!(),
        };
    }
}
