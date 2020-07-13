// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod error;
pub mod linux_plugin_transforms;

pub use error::ImlDeviceError;

use device_types::{devices::Device, mount::Mount};
use futures::{future::try_join_all, lock::Mutex};
use im::HashSet;
use iml_postgres::sqlx::{self, PgPool};
use iml_tracing::tracing;
use iml_wire_types::Fqdn;
use std::{
    collections::{BTreeSet, HashMap},
    sync::Arc,
};

pub type Cache = Arc<Mutex<HashMap<Fqdn, Device>>>;

/// Given a db pool, create a new cache and fill it with initial data.
/// This will start the device tree with the previous items it left off with.
pub async fn create_cache(pool: &PgPool) -> Result<Cache, ImlDeviceError> {
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

pub async fn update_devices(
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

pub async fn client_mount_content_id(pool: &PgPool) -> Result<Option<i32>, ImlDeviceError> {
    let id = sqlx::query!("select id from django_content_type where model = 'lustreclientmount'")
        .fetch_optional(pool)
        .await?
        .map(|x| x.id);

    Ok(id)
}

pub async fn update_client_mounts(
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

    let mount_map = mounts
        .into_iter()
        .filter(|m| m.fs_type.0 == "lustre")
        .filter_map(|m| {
            m.source
                .0
                .to_str()
                .and_then(|p| p.splitn(2, ":/").nth(1))
                .map(|fs| (fs.to_string(), m.target.0.to_string_lossy().to_string()))
        })
        .fold(HashMap::new(), |mut acc, (fs_name, mountpoint)| {
            let mountpoints = acc.entry(fs_name).or_insert_with(|| BTreeSet::new());

            mountpoints.insert(mountpoint);

            acc
        });

    tracing::debug!("Client mounts at {}({}): {:?}", host, host_id, &mount_map);

    let xs = mount_map.into_iter().map(|(fs_name, mountpoints)| async move {
        let mountpoints:Vec<String> = mountpoints.into_iter().collect();

        let x = sqlx::query!(
            r#"
        INSERT INTO chroma_core_lustreclientmount
        (host_id, filesystem, mountpoints, state, state_modified_at, immutable_state, not_deleted, content_type_id)
        VALUES ($1, $2, $3, 'mounted', now(), 'f', 't', $4)
        ON CONFLICT (host_id, filesystem, not_deleted) DO UPDATE
        SET 
            mountpoints = excluded.mountpoints,
            state = excluded.state,
            state_modified_at = excluded.state_modified_at
        RETURNING id
    "#,
            host_id,
            &fs_name,
            &mountpoints,
            ct_id,
        ).fetch_all(pool).await?;

        Ok::<_, ImlDeviceError>(x)
    });

    let xs: Vec<_> = try_join_all(xs)
        .await?
        .into_iter()
        .flatten()
        .map(|x| x.id)
        .collect();

    let updated = sqlx::query!(
        r#"
            UPDATE chroma_core_lustreclientmount
            SET 
                mountpoints = array[]::text[],
                state = 'unmounted',
                state_modified_at = now()
            WHERE host_id = $1
            AND id != ALL($2)
        "#,
        host_id,
        &xs
    )
    .execute(pool)
    .await?;

    tracing::debug!("Updated client mounts: {:?}", updated);

    Ok(())
}
