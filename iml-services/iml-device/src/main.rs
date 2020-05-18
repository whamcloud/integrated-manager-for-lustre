// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::{devices::Device, mount::Mount};
use diesel::{self, dsl, pg::upsert::excluded, prelude::*, sql_types};
use futures::{lock::Mutex, TryFutureExt, TryStreamExt};
use im::HashSet;
use iml_device::{
    linux_plugin_transforms::{
        build_device_lookup, devtree2linuxoutput, get_shared_pools, populate_zpool, update_vgs,
        LinuxPluginData,
    },
    ImlDeviceError,
};
use iml_orm::{
    models::{ChromaCoreDevice, ChromaCoreLustreclientmount, NewChromaCoreDevice},
    schema::{
        chroma_core_device as dvc, chroma_core_lustreclientmount as clmnt,
        chroma_core_managedfilesystem as fs, chroma_core_managedhost as host,
        django_content_type as djct,
    },
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
    let data: HashMap<Fqdn, Device> = dvc::table
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

async fn update_devices(pool: &DbPool, host: &Fqdn, devices: &Device) {
    let device_to_insert = NewChromaCoreDevice {
        fqdn: host.to_string(),
        devices: serde_json::to_value(devices)
            .expect("Could not convert incoming Devices to JSON."),
    };

    let new_device = diesel::insert_into(dvc::table)
        .values(device_to_insert)
        .on_conflict(dvc::fqdn)
        .do_update()
        .set(dvc::devices.eq(excluded(dvc::devices)))
        .get_result_async::<ChromaCoreDevice>(&pool)
        .await;
    match new_device {
        Ok(d) => {
            tracing::info!("Inserted devices from host '{}'", host);
            tracing::debug!("Inserted {:?}", d);
        }
        Err(e) => {
            tracing::error!("Error saving new devices: {}", e);
        }
    }
}

async fn update_client_mounts(
    pool: &DbPool,
    ct_id: Option<i32>,
    host: &Fqdn,
    mounts: &HashSet<Mount>,
) {
    let host_id = match host::table
        .select(host::id)
        .filter(host::fqdn.eq(host.to_string()))
        .get_result_async::<i32>(&pool)
        .await
    {
        Ok(id) => {
            tracing::debug!("Host id: {}", id);
            id
        }
        Err(e) => {
            tracing::error!("Host '{}' is unknown: {}", host, e);
            return;
        }
    };

    let lustre_mounts = mounts
        .into_iter()
        .filter(|m| m.fs_type.0.as_str() == "lustre")
        .filter_map(|m| {
            m.source
                .0
                .to_str()
                .and_then(|p| p.splitn(2, ":/").nth(1))
                .map(|fs| (fs.to_string(), m.target.0.to_str().map(String::from)))
        })
        .collect::<Vec<_>>();

    tracing::debug!("Client mounts at {}: {:?}", host, &lustre_mounts);

    let state_modified_at = chrono::offset::Utc::now().into_sql::<sql_types::Timestamptz>();

    let insert_mounts = lustre_mounts
        .iter()
        .map(|(fs, tg)| {
            let mp = tg
                .clone()
                .into_sql::<sql_types::Nullable<sql_types::Text>>();
            fs::table
                .select((
                    host_id.into_sql::<sql_types::Integer>(),
                    fs::id,
                    mp,
                    "mounted".as_sql::<sql_types::Text>(),
                    state_modified_at,
                    false.into_sql::<sql_types::Bool>(),
                    Some(true).into_sql(),
                    ct_id.into_sql(),
                ))
                .filter(fs::name.eq(fs.clone()))
                .insert_into(clmnt::table)
                .into_columns((
                    clmnt::host_id,
                    clmnt::filesystem_id,
                    clmnt::mountpoint,
                    clmnt::state,
                    clmnt::state_modified_at,
                    clmnt::immutable_state,
                    clmnt::not_deleted,
                    clmnt::content_type_id,
                ))
                .on_conflict((clmnt::host_id, clmnt::filesystem_id, clmnt::not_deleted))
                .do_update()
                .set((
                    clmnt::mountpoint.eq(excluded(clmnt::mountpoint)),
                    clmnt::state.eq(excluded(clmnt::state)),
                    clmnt::state_modified_at.eq(state_modified_at),
                ))
                .get_result_async::<ChromaCoreLustreclientmount>(&pool)
        })
        .collect::<Vec<_>>();

    let mounts = futures::future::join_all(insert_mounts).await;

    for m in &mounts {
        match m {
            Ok(x) => tracing::debug!("Inserted {:?}", x),
            Err(e) => tracing::error!("Failed to insert client mount {:?}", e),
        }
    }

    let fs_ids: Vec<i32> = mounts
        .into_iter()
        .filter_map(Result::ok)
        .map(|c| c.filesystem_id)
        .collect();
    let updated = diesel::update(clmnt::table)
        .filter(clmnt::filesystem_id.ne(dsl::all(fs_ids)))
        .filter(clmnt::host_id.eq(host_id))
        .set((
            clmnt::mountpoint.eq(Option::<String>::None),
            clmnt::state.eq("unmounted".as_sql::<sql_types::Text>()),
            clmnt::state_modified_at.eq(state_modified_at),
        ))
        .get_results_async::<ChromaCoreLustreclientmount>(&pool)
        .await;

    match updated {
        Ok(u) => tracing::debug!("Updated {:?}", u),
        Err(e) => tracing::error!("Failed to update client mounts: {:?}", e),
    }
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

    let mut s = consume_data::<(Device, HashSet<Mount>)>("rust_agent_device_rx");

    // Django's artefact:
    let lustreclientmount_ct_id = djct::table
        .select(djct::id)
        .filter(djct::model.eq("lustreclientmount"))
        .first_async::<i32>(&pool)
        .await
        .ok();

    while let Some((host, (devices, mounts))) = s.try_next().await? {
        let mut cache = cache2.lock().await;
        cache.insert(host.clone(), devices.clone());

        update_devices(&pool, &host, &devices).await;
        update_client_mounts(&pool, lustreclientmount_ct_id, &host, &mounts).await;
    }

    Ok(())
}
