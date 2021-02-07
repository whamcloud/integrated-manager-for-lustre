// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate emf_device;

use chrono::{DateTime, Utc};
use device_types::{
    mount::{FsType, Mount, MountOpts, MountPoint},
    DevicePath,
};
use emf_device::update_client_mounts;
use emf_postgres::sqlx;
use emf_wire_types::Fqdn;
use insta::assert_json_snapshot;
use std::error::Error;

#[derive(serde::Serialize)]
struct ClientMount {
    id: i32,
    state_modified_at: DateTime<Utc>,
    state: String,
    filesystem: String,
    host_id: i32,
    mountpoints: Vec<String>,
}

#[tokio::test]
#[ignore = "Requires an active and populated DB"]
async fn test_insert() -> Result<(), Box<dyn Error>> {
    let pool = emf_postgres::test_setup().await?;

    sqlx::query!(
        r#"INSERT INTO host
        (
            machine_id,
            state,
            fqdn,
            boot_time
        ) VALUES
        ('1234', 'unconfigured', 'foo.bar', now())
        ON CONFLICT DO NOTHING"#
    )
    .execute(&pool)
    .await?;

    let mut mounts = im::HashSet::new();

    mounts.insert(Mount::new(
        MountPoint("/mnt/part1".into()),
        DevicePath("/dev/sde1".into()),
        FsType("ext4".to_string()),
        MountOpts("rw,relatime,data=ordered".to_string()),
    ));

    mounts.insert(Mount::new(
        MountPoint("/mnt/fs0a9c".into()),
        DevicePath("172.60.0.40@o2ib,172.60.0.44@o2ib:172.60.0.42@o2ib,172.60.0.46@o2ib:172.60.0.43@o2ib,172.60.0.47@o2ib:172.60.0.41@o2ib,172.60.0.45@o2ib:/fs0a9c".into()),
        FsType("lustre".into()),
        MountOpts("rw,flock,lazystatfs".into())
    ));

    mounts.insert(Mount::new(
        MountPoint("/mnt/fs0a9c2".into()),
        DevicePath("172.60.0.40@o2ib,172.60.0.44@o2ib:172.60.0.42@o2ib,172.60.0.46@o2ib:172.60.0.43@o2ib,172.60.0.47@o2ib:172.60.0.41@o2ib,172.60.0.45@o2ib:/fs0a9c".into()),
        FsType("lustre".into()),
        MountOpts("rw,flock,lazystatfs".into())
    ));

    // Add some mounts
    update_client_mounts(&pool, &Fqdn("foo.bar".into()), &mounts).await?;

    let xs = sqlx::query_as!(ClientMount, r#"SELECT * FROM lustreclientmount"#)
        .fetch_all(&pool)
        .await?;

    assert_json_snapshot!(xs, {
        "[].id" => "<ID>",
        "[].state_modified_at" => "<STATE_MODIFIED_AT>",
        "[].host_id" => "<HOST_ID>"
    });

    // Remove Some mounts
    update_client_mounts(&pool, &Fqdn("foo.bar".into()), &im::hashset![Mount::new(
        MountPoint("/mnt/fs0a9c2".into()),
        DevicePath("172.60.0.40@o2ib,172.60.0.44@o2ib:172.60.0.42@o2ib,172.60.0.46@o2ib:172.60.0.43@o2ib,172.60.0.47@o2ib:172.60.0.41@o2ib,172.60.0.45@o2ib:/fs0a9c".into()),
        FsType("lustre".into()),
        MountOpts("rw,flock,lazystatfs".into())
    )]).await?;

    let xs = sqlx::query_as!(ClientMount, r#"SELECT * FROM lustreclientmount"#)
        .fetch_all(&pool)
        .await?;

    assert_json_snapshot!(xs, {
        "[].id" => "<ID>",
        "[].state_modified_at" => "<STATE_MODIFIED_AT>",
        "[].host_id" => "<HOST_ID>"
    });

    // Remove all mounts
    update_client_mounts(&pool, &Fqdn("foo.bar".into()), &im::hashset![]).await?;

    let xs = sqlx::query_as!(ClientMount, r#"SELECT * FROM lustreclientmount"#)
        .fetch_all(&pool)
        .await?;

    assert_json_snapshot!(xs, {
        "[].id" => "<ID>",
        "[].state_modified_at" => "<STATE_MODIFIED_AT>",
        "[].host_id" => "<HOST_ID>"
    });

    Ok(())
}
