// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod error;
pub mod linux_plugin_transforms;

pub use error::ImlDeviceError;

use device_types::mount::Mount;
use futures::future::try_join_all;
use im::HashSet;
use iml_tracing::tracing;
use iml_wire_types::Fqdn;
use sqlx::postgres::{PgConnectOptions, PgPool};
use std::collections::{BTreeSet, HashMap};

pub async fn get_db_pool() -> Result<PgPool, ImlDeviceError> {
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
