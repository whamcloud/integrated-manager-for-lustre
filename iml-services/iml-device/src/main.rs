// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::{devices::Device, mount::Mount};
use futures::{lock::Mutex, TryFutureExt, TryStreamExt};
use im::HashSet;
use iml_device::{
    linux_plugin_transforms::{
        build_device_lookup, devtree2linuxoutput, get_shared_pools, populate_zpool, update_vgs,
        LinuxPluginData,
    },
    ImlDeviceError,
};
use iml_service_queue::service_queue::consume_data;
use iml_tracing::tracing;
use iml_wire_types::Fqdn;
use sqlx::postgres::{PgConnectOptions, PgPool};
use std::{
    collections::{BTreeMap, HashMap},
    sync::Arc,
};
use warp::Filter;

type Cache = Arc<Mutex<HashMap<Fqdn, Device>>>;

async fn get_db_pool() -> Result<PgPool, ImlDeviceError> {
    let mut opts = PgConnectOptions::default().username(&iml_manager_env::get_db_user());

    opts = if let Some(x) = iml_manager_env::get_db_host() {
        opts.host(&x)
    } else {
        opts
    };

    opts = if let Some(x) = iml_manager_env::get_db_name() {
        opts.database(&x)
    } else {
        opts
    };

    opts = if let Some(x) = iml_manager_env::get_db_password() {
        opts.password(&x)
    } else {
        opts
    };

    let x = PgPool::builder().max_size(5).build_with(opts).await?;

    Ok(x)
}

/// Given a db pool, create a new cache and fill it with initial data.
/// This will start the device tree with the previous items it left off with.
async fn create_cache(pool: &PgPool) -> Result<Cache, ImlDeviceError> {
    let data = sqlx::query!("select * from chroma_core_device")
        .fetch_all(pool)
        .await?
        .into_iter()
        .map(|x| -> Result<(Fqdn, Device), ImlDeviceError> {
            let d = serde_json::from_value(x.devices)?;

            Ok((Fqdn(x.fqdn), d))
        })
        .collect::<Result<_, _>>()?;

    Ok(Arc::new(Mutex::new(data)))
}

async fn update_devices(
    pool: &PgPool,
    host: &Fqdn,
    devices: &Device,
) -> Result<(), ImlDeviceError> {
    tracing::info!("Inserting devices from host '{}'", host);
    tracing::debug!("Inserting {:?}", devices);

    sqlx::query!(
        r#"
        INSERT INTO chroma_core_device
        (fqdn, devices)
        VALUES ($1, $2)
        ON CONFLICT (fqdn) DO UPDATE
        SET devices = EXCLUDED.devices
    "#,
        host.to_string(),
        serde_json::to_value(devices)?
    )
    .execute(pool)
    .await?;

    Ok(())
}

async fn update_client_mounts(
    pool: &PgPool,
    ct_id: Option<i32>,
    host: &Fqdn,
    mounts: &HashSet<Mount>,
) -> Result<(), ImlDeviceError> {
    let host_id: Option<i32> = sqlx::query!(
        "select id from chroma_core_managedhost where fqdn = $1 and not_deleted = 't'",
        host.to_string()
    )
    .fetch_optional(pool)
    .await?
    .map(|x| x.id);

    let host_id = match host_id {
        Some(id) => id,
        None => {
            tracing::warn!("Host '{}' is unknown", host);

            return Ok(());
        }
    };

    let (filesystems, mountpoints): (Vec<_>, Vec<_>) = mounts
        .into_iter()
        .filter(|m| m.fs_type.0 == "lustre")
        .filter_map(|m| {
            m.source
                .0
                .to_str()
                .and_then(|p| p.splitn(2, ":/").nth(1))
                .map(|fs| (fs.to_string(), m.target.0.to_string_lossy().to_string()))
        })
        .unzip();

    tracing::debug!(
        "Client mounts at {}({}): {:?} {:?}",
        host,
        host_id,
        &filesystems,
        &mountpoints
    );

    let ids: Vec<_> = sqlx::query!(
    r#"
        INSERT INTO chroma_core_lustreclientmount
        (host_id, filesystem, mountpoint, state, state_modified_at, immutable_state, not_deleted, content_type_id)
        SELECT $1, filesystem, mountpoint, 'mounted', now(), 'f', 't', $4
        FROM UNNEST($2::text[], $3::text[])
        AS t(filesystem, mountpoint)
        ON CONFLICT (host_id, filesystem, not_deleted) DO UPDATE
        SET 
            mountpoint = excluded.mountpoint,
            state = excluded.state,
            state_modified_at = excluded.state_modified_at
        RETURNING id
    "#,
        host_id,
        &filesystems,
        &mountpoints,
        ct_id,
    ).fetch_all(pool).await?
        .into_iter()
        .map(|x| x.id)
        .collect();

    let updated = sqlx::query!(
        r#"
            UPDATE chroma_core_lustreclientmount
            SET 
                mountpoint = Null,
                state = 'unmounted',
                state_modified_at = now()
            WHERE host_id = $1
            AND id != ALL($2)
        "#,
        host_id,
        &ids
    )
    .execute(pool)
    .await?;

    tracing::debug!("Updated client mounts: {:?}", updated);

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), ImlDeviceError> {
    iml_tracing::init();

    let addr = iml_manager_env::get_device_aggregator_addr();

    let pool = get_db_pool().await?;

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

    // Django's artifact:
    let lustreclientmount_ct_id =
        sqlx::query!("select id from django_content_type where model = 'lustreclientmount'")
            .fetch_optional(&pool)
            .await?
            .map(|x| x.id);

    while let Some((host, (devices, mounts))) = s.try_next().await? {
        update_devices(&pool, &host, &devices).await?;
        update_client_mounts(&pool, lustreclientmount_ct_id, &host, &mounts).await?;

        let mut cache = cache2.lock().await;
        cache.insert(host, devices);
    }

    Ok(())
}
