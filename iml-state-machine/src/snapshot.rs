// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Error;
use iml_postgres::{active_mgs_host_fqdn, PgPool};
use iml_wire_types::{
    snapshot::{Create, Destroy, Mount, Unmount},
    Fqdn,
};

pub async fn mount_snapshot(pool: PgPool, x: Mount) -> Result<(Fqdn, String, Mount), Error> {
    let fqdn = get_active_mgs_or_fail(&pool, &x.fsname).await?;

    Ok((fqdn, "snapshot_mount".to_string(), x))
}

pub async fn unmount_snapshot(pool: PgPool, x: Unmount) -> Result<(Fqdn, String, Unmount), Error> {
    let fqdn = get_active_mgs_or_fail(&pool, &x.fsname).await?;

    Ok((fqdn, "snapshot_unmount".to_string(), x))
}

pub async fn destroy_snapshot(pool: PgPool, x: Destroy) -> Result<(Fqdn, String, Destroy), Error> {
    let fqdn = get_active_mgs_or_fail(&pool, &x.fsname).await?;

    Ok((fqdn, "snapshot_destroy".to_string(), x))
}

pub async fn create_snapshot(pool: PgPool, x: Create) -> Result<(Fqdn, String, Create), Error> {
    let fqdn = get_active_mgs_or_fail(&pool, &x.fsname).await?;

    Ok((fqdn, "snapshot_create".to_string(), x))
}

async fn get_active_mgs_or_fail(pool: &PgPool, fsname: &str) -> Result<Fqdn, Error> {
    match active_mgs_host_fqdn(fsname, pool).await? {
        Some(x) => Ok(Fqdn(x)),
        None => Err(Error::NotFound),
    }
}
