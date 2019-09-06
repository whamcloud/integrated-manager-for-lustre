// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    change::{self, Change},
    error::ImlDevicesError,
};
use iml_postgres::Transaction;
use iml_wire_types::{
    db::{Device, DeviceHost, DeviceId, DeviceIds, DeviceType, MountPath, Paths, Size},
    Fqdn,
};
use std::{
    collections::{BTreeMap, BTreeSet},
    path::PathBuf,
};

pub type FlatDevices = BTreeMap<DeviceId, FlatDevice>;

pub type Devices = BTreeMap<DeviceId, Device>;

pub type DeviceHosts = BTreeMap<DeviceId, DeviceHost>;

/// A device (Block or Virtual).
/// These should be unique per cluster
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct FlatDevice {
    pub id: DeviceId,
    pub size: u64,
    pub device_type: DeviceType,
    pub parents: BTreeSet<DeviceId>,
    // pub usable_for_lustre: bool,
    pub children: BTreeSet<DeviceId>,
    pub paths: BTreeSet<PathBuf>,
    pub mount_path: Option<PathBuf>,
    pub fs_type: Option<String>,
    pub fs_label: Option<String>,
    pub fs_uuid: Option<String>,
}

fn create_dev(flat_dev: FlatDevice, fqdn: Fqdn) -> ((DeviceId, Device), (DeviceId, DeviceHost)) {
    let d = Device {
        id: flat_dev.id.clone(),
        size: Size(flat_dev.size),
        device_type: flat_dev.device_type,
        parents: DeviceIds(flat_dev.parents),
        children: DeviceIds(flat_dev.children),
        // usable_for_lustre: flat_dev.usable_for_lustre,
        usable_for_lustre: false,
    };

    let dh = DeviceHost {
        device_id: flat_dev.id.clone(),
        fqdn,
        local: true,
        paths: Paths(flat_dev.paths),
        mount_path: MountPath(flat_dev.mount_path),
        fs_type: flat_dev.fs_type,
        fs_label: flat_dev.fs_label,
        fs_uuid: flat_dev.fs_uuid,
    };

    ((flat_dev.id.clone(), d), (flat_dev.id, dh))
}

pub fn convert_flat_devices(flat_devices: FlatDevices, fqdn: Fqdn) -> (Devices, DeviceHosts) {
    flat_devices
        .into_iter()
        .map(|x| create_dev(x.1, fqdn.clone()))
        .unzip()
}

fn get_local_device_hosts<'a>(
    device_hosts: &'a BTreeMap<Fqdn, DeviceHosts>,
    fqdn: &Fqdn,
) -> BTreeMap<&'a DeviceId, &'a DeviceHost> {
    match device_hosts.get(&fqdn) {
        Some(dhs) => dhs
            .iter()
            .filter(|(_k, v)| &v.fqdn == fqdn && v.local)
            .collect(),
        None => BTreeMap::new(),
    }
}

async fn insert_device_host(
    transaction: &mut Transaction<'_>,
    fqdn: &Fqdn,
    x: &DeviceHost,
) -> Result<(), ImlDevicesError> {
    let s = transaction.prepare("INSERT INTO chroma_core_devicehost (device_id, fqdn, local, paths, mount_path, fs_type, fs_label, fs_uuid) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)").await?;

    transaction
        .execute(
            &s,
            &[
                &x.device_id,
                &fqdn.0,
                &x.local,
                &x.paths,
                &x.mount_path,
                &x.fs_type,
                &x.fs_label,
                &x.fs_uuid,
            ],
        )
        .await?;

    Ok(())
}

async fn update_device_host(
    transaction: &mut Transaction<'_>,
    fqdn: &Fqdn,
    x: &DeviceHost,
) -> Result<(), ImlDevicesError> {
    let s = transaction.prepare("UPDATE chroma_core_devicehost SET local = $3, paths = $4, mount_path = $5, fs_type = $6, fs_label= $7, fs_uuid=$8 WHERE device_id = $1 AND fqdn = $2").await?;

    transaction
        .execute(
            &s,
            &[
                &x.device_id,
                &fqdn.0,
                &x.local,
                &x.paths,
                &x.mount_path,
                &x.fs_type,
                &x.fs_label,
                &x.fs_uuid,
            ],
        )
        .await?;

    Ok(())
}

async fn remove_device_host(
    transaction: &mut Transaction<'_>,
    fqdn: &Fqdn,
    id: &DeviceId,
) -> Result<(), ImlDevicesError> {
    let s = transaction
        .prepare("DELETE FROM chroma_core_devicehost WHERE device_id = $1 AND fqdn = $2")
        .await?;

    transaction.execute(&s, &[id, &fqdn.0]).await?;

    Ok(())
}

pub async fn persist_local_device_hosts<'a>(
    mut transaction: &mut Transaction<'a>,
    fqdn: &Fqdn,
    dhs: &DeviceHosts,
    db_dhs: &BTreeMap<Fqdn, DeviceHosts>,
) -> Result<(), ImlDevicesError> {
    let local_dhs = get_local_device_hosts(&db_dhs, &fqdn);

    for c in change::get_changes_values(&local_dhs, &dhs.iter().collect()) {
        match c {
            Change::Add(d) => {
                tracing::info!("Going to insert new devicehost {:?}, {:?}", fqdn, d);

                insert_device_host(&mut transaction, &fqdn, d).await?;
            }
            Change::Update(d) => {
                tracing::info!("Going to update devicehost {:?}, {:?}", fqdn, d);

                update_device_host(&mut transaction, &fqdn, d).await?;
            }
            Change::Remove(d) => {
                tracing::info!("Going to remove devicehost {:?}, {:?}", fqdn, d);

                remove_device_host(&mut transaction, &fqdn, &d.device_id).await?;
            }
        };
    }

    Ok(())
}

pub async fn persist_devices<'a>(
    transaction: &mut Transaction<'a>,
    devices: &Devices,
    db_devices: &Devices,
) -> Result<(), ImlDevicesError> {
    for c in change::get_changes_values(&db_devices.iter().collect(), &devices.iter().collect()) {
        match c {
            Change::Add(d) => {
                tracing::info!("Going to add device {:?}", d);

                let s = transaction.prepare("INSERT INTO chroma_core_device (id, size, usable_for_lustre, device_type, parents, children) VALUES ($1, $2, $3, $4, $5, $6)").await?;

                transaction
                    .execute(
                        &s,
                        &[
                            &d.id,
                            &d.size,
                            &d.usable_for_lustre,
                            &d.device_type,
                            &d.parents,
                            &d.children,
                        ],
                    )
                    .await?;
            }
            Change::Update(d) => {
                tracing::info!("Going to update device {:?}", d);

                let s = transaction.prepare("UPDATE chroma_core_device SET size = $2, usable_for_lustre = $3, device_type = $4, parents=$5, children=$6 WHERE id = $1").await?;

                transaction
                    .execute(
                        &s,
                        &[
                            &d.id,
                            &d.size,
                            &d.usable_for_lustre,
                            &d.device_type,
                            &d.parents,
                            &d.children,
                        ],
                    )
                    .await?;
            }
            Change::Remove(d) => {
                tracing::info!("Going to remove device {:?}", d);

                let s = transaction
                    .prepare("DELETE FROM chroma_core_device WHERE id = $1")
                    .await?;

                transaction.execute(&s, &[&d.id]).await?;
            }
        }
    }

    Ok(())
}

pub async fn perform_updates<'a>(
    mut transaction: &mut Transaction<'a>,
    fqdn: Fqdn,
    dhs: DeviceHosts,
    devices: Devices,
    db_dhs: BTreeMap<Fqdn, DeviceHosts>,
    db_devices: Devices,
) -> Result<(), ImlDevicesError> {
    let local_dhs = get_local_device_hosts(&db_dhs, &fqdn);

    let dhs_changes = change::get_changes(&local_dhs, &dhs.iter().collect())
        .into_iter()
        .map(|c| c.map(|x| (fqdn.clone(), x.clone())))
        .collect::<Vec<_>>();

    let other_hosts: Vec<_> = db_dhs
        .iter()
        .filter(|(k, _)| k != &&fqdn)
        .flat_map(|(_, xs)| xs.values())
        .filter(|x| !x.local)
        .collect();

    let remote_dhs_changes: Vec<Change<(Fqdn, DeviceId)>> = other_hosts
        .iter()
        .filter(|x| local_dhs.contains_key(&x.device_id))
        .fold(vec![], |mut acc, x| {
            let change = dhs_changes.iter().find(|&y| y.1 == x.device_id);

            if let Some(change) = change {
                match change {
                    Change::Add(v) => tracing::warn!(
                        "Unexepected Add when comparing {:?} (remote) with {:?} (local)",
                        x,
                        v
                    ),
                    Change::Update(v) => acc.push(Change::Update((x.fqdn.clone(), v.1.clone()))),
                    Change::Remove(v) => acc.push(Change::Remove((x.fqdn.clone(), v.1.clone()))),
                }
            }

            acc
        });

    let device_changes =
        change::get_changes(&db_devices.iter().collect(), &devices.iter().collect());

    // 3. Find any new non-local devices and ensure they are present on all relevant nodes.
    let remote_dhs_changes = device_changes
        .iter()
        .filter(|x| x.is_add())
        .filter_map(|x| devices.get(x))
        .fold(remote_dhs_changes, |mut acc, x| {
            for (fqdn, ys) in db_dhs.iter() {
                if x.parents
                    .iter()
                    .collect::<BTreeSet<&DeviceId>>()
                    .is_subset(&ys.keys().collect())
                {
                    acc.push(Change::Add((fqdn.clone(), x.id.clone())));
                }
            }

            acc
        });

    // 4. Insert changes into the DB
    for c in remote_dhs_changes {
        match c {
            Change::Add((fqdn, id)) => {
                tracing::info!("Going to insert new remote devicehost {:?}, {:?}", fqdn, id);

                let x = dhs.get(&id).unwrap();

                insert_device_host(&mut transaction, &fqdn, x).await?;
            }
            Change::Update((fqdn, id)) => {
                tracing::info!("Going to update remote devicehost {:?}, {:?}", fqdn, id);

                let x = dhs.get(&id).unwrap();

                update_device_host(&mut transaction, &fqdn, x).await?;
            }
            Change::Remove((fqdn, id)) => {
                tracing::info!("Going to delete remote devicehost {:?}, {:?}", fqdn, id);

                remove_device_host(&mut transaction, &fqdn, &id).await?;
            }
        }
    }

    Ok(())
}

// #[cfg(test)]
// mod tests {
//     use super::*;
//     use iml_wire_types::Fqdn;
//     use insta::assert_debug_snapshot;
//     use serde_json;
//     use std::fs;

//     #[test]
//     fn test_dev_tree_conversion() {
//         let f = fs::read_to_string("./fixtures.json").unwrap();
//         let x = serde_json::from_str(&f).unwrap();

//         let fqdn = Fqdn("host1".into());

//         let mut dhs = DeviceHosts::default();

//         let mut ds = Devices::default();

//         process_tree(&x, &fqdn, None, &mut dhs, &mut ds);

//         assert_debug_snapshot!("device hosts", dhs);
//         assert_debug_snapshot!("devices", ds);
//     }
// }
