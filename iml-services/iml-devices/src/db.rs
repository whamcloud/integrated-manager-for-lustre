// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    change::{self, Change},
    error::ImlDevicesError,
};
use futures::TryStreamExt;
use iml_postgres::{connect, select_all, Client, Transaction};
use iml_wire_types::{
    db::{Device, DeviceHost, DeviceId, DeviceIds, DeviceType, MountPath, Name, Paths, Size},
    Fqdn,
};
use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    iter,
    path::PathBuf,
};

pub type FlatDevices = BTreeMap<DeviceId, FlatDevice>;

pub type Devices = BTreeMap<DeviceId, Device>;

pub type DevicesRef<'a> = BTreeMap<&'a DeviceId, &'a Device>;

pub type DeviceHostKey = (DeviceId, Fqdn);

pub type DeviceHosts = BTreeMap<DeviceHostKey, DeviceHost>;

pub type DeviceHostsRef<'a> = BTreeMap<&'a DeviceHostKey, &'a DeviceHost>;

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

fn create_dev(
    flat_dev: FlatDevice,
    fqdn: Fqdn,
) -> ((DeviceId, Device), (DeviceHostKey, DeviceHost)) {
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

    (
        (flat_dev.id.clone(), d),
        ((flat_dev.id, dh.fqdn.clone()), dh),
    )
}

pub fn convert_flat_devices(flat_devices: FlatDevices, fqdn: Fqdn) -> (Devices, DeviceHosts) {
    flat_devices
        .into_iter()
        .map(|x| create_dev(x.1, fqdn.clone()))
        .unzip()
}

fn get_fqdns<'a>(device_hosts: &'a DeviceHosts) -> impl Iterator<Item = &'a Fqdn> {
    device_hosts.iter().map(|((d, fqdn), v)| fqdn)
}

/// Given a device id and some `DeviceHosts`,
/// filter to the cooresponding hosts.
fn filter_device_hosts<'a>(
    id: &'a DeviceId,
    device_hosts: &'a DeviceHosts,
) -> impl Iterator<Item = (&'a DeviceHostKey, &'a DeviceHost)> {
    device_hosts.iter().filter(move |(_, v)| &v.device_id == id)
}

/// Given a device id and some `DeviceHosts`,
/// try to find the first cooresponding host.
fn find_device_host<'a>(
    id: &'a DeviceId,
    device_hosts: &'a DeviceHostsRef<'a>,
) -> Option<(&'a &'a DeviceHostKey, &'a &'a DeviceHost)> {
    device_hosts
        .into_iter()
        .find(move |(_, v)| &v.device_id == id)
}

pub fn get_local_device_hosts<'a>(
    device_hosts: &'a DeviceHosts,
    fqdn: &Fqdn,
) -> DeviceHostsRef<'a> {
    device_hosts
        .into_iter()
        .filter(|(_k, v)| &v.fqdn == fqdn && v.local)
        .collect()
}

pub fn get_local_devices<'a>(
    local_device_hosts: &DeviceHostsRef<'_>,
    devices: &'a Devices,
) -> DevicesRef<'a> {
    devices
        .into_iter()
        .filter(|(k, _)| {
            local_device_hosts
                .into_iter()
                .find(|(_, v)| &&v.device_id == k)
                .is_some()
        })
        .collect()
}

pub fn get_other_device_hosts<'a>(
    db_device_hosts: &'a DeviceHosts,
    fqdn: &'a Fqdn,
) -> DeviceHostsRef<'a> {
    db_device_hosts
        .iter()
        .filter(move |(_, v)| &v.fqdn != fqdn)
        .collect()
}

pub fn get_devices_by_device_host<'a>(
    device_hosts: &'a DeviceHostsRef<'a>,
    devices: &'a Devices,
) -> DevicesRef<'a> {
    devices
        .iter()
        .filter(move |(k, _)| find_device_host(&k, device_hosts).is_some())
        .collect()
}

pub async fn get_db_devices(mut client: &mut Client) -> Result<Devices, iml_postgres::Error> {
    select_all(
        &mut client,
        &format!("SELECT * FROM {}", Device::table_name()),
        iter::empty(),
    )
    .await?
    .map_ok(Device::from)
    .map_ok(|x| (x.id.clone(), x))
    .try_collect()
    .await
}

pub async fn get_db_device_hosts(
    mut client: &mut Client,
) -> Result<Vec<DeviceHost>, iml_postgres::Error> {
    select_all(
        &mut client,
        &format!("SELECT * FROM {}", DeviceHost::table_name()),
        iter::empty(),
    )
    .await?
    .map_ok(DeviceHost::from)
    .try_collect()
    .await
}

async fn insert_device_host(
    transaction: &mut Transaction<'_>,
    fqdn: &Fqdn,
    x: &DeviceHost,
) -> Result<(), ImlDevicesError> {
    let s = transaction.prepare(
        &format!("INSERT INTO {} (device_id, fqdn, local, paths, mount_path, fs_type, fs_label, fs_uuid) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", DeviceHost::table_name())
    ).await?;

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
    let s = transaction.prepare(&format!("UPDATE {} SET local = $3, paths = $4, mount_path = $5, fs_type = $6, fs_label= $7, fs_uuid=$8 WHERE device_id = $1 AND fqdn = $2", DeviceHost::table_name())).await?;

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
        .prepare(&format!(
            "DELETE FROM {} WHERE device_id = $1 AND fqdn = $2",
            DeviceHost::table_name()
        ))
        .await?;

    transaction.execute(&s, &[id, &fqdn.0]).await?;

    Ok(())
}

pub async fn persist_local_device_hosts<'a>(
    mut transaction: &mut Transaction<'a>,
    incoming_devices: &DeviceHosts,
    local_db_device_hosts: &DeviceHostsRef<'_>,
) -> Result<(), ImlDevicesError> {
    for c in change::get_changes_values(local_db_device_hosts, &incoming_devices.iter().collect()) {
        match c {
            Change::Add(d) => {
                tracing::debug!(
                    "Going to insert new devicehost {:?}, {:?}",
                    d.fqdn,
                    d.device_id
                );

                insert_device_host(&mut transaction, &d.fqdn, d).await?;
            }
            Change::Update(d) => {
                tracing::debug!("Going to update devicehost {:?}, {:?}", d.fqdn, d.device_id);

                update_device_host(&mut transaction, &d.fqdn, d).await?;
            }
            Change::Remove(d) => {
                tracing::debug!("Going to remove devicehost {:?}, {:?}", d.fqdn, d.device_id);

                remove_device_host(&mut transaction, &d.fqdn, &d.device_id).await?;
            }
        };
    }

    Ok(())
}

pub async fn persist_local_devices<'a>(
    transaction: &mut Transaction<'a>,
    incoming_devices: &Devices,
    other_devices: &DevicesRef<'a>,
    local_db_devices: &DevicesRef<'a>,
) -> Result<(), ImlDevicesError> {
    for c in change::get_changes_values(&local_db_devices, &incoming_devices.iter().collect()) {
        match c {
            Change::Add(d) => {
                if other_devices.get(&d.id).is_some() {
                    tracing::info!("Device {:?} already added by another host.", d.id);
                    continue;
                }

                tracing::debug!("Going to add device {:?}", d.id);

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
                tracing::debug!("Going to update device {:?}", d.id);

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
                // @TODO: I think devices should probably not be deleted.
                // Orphan devices should probably be surfaced as alerts.
                tracing::debug!("Going to remove device {:?}", d.id);

                let s = transaction
                    .prepare(&format!(
                        "DELETE FROM {} WHERE id = $1",
                        Device::table_name()
                    ))
                    .await?;

                transaction.execute(&s, &[&d.id]).await?;
            }
        }
    }

    Ok(())
}

/// Some devices should appear on multiple hosts even if they are physically existent on one host.
///
/// Examples are Zpools / Datasets, LVs / VGs and MdRaid.
pub async fn update_virtual_devices<'a>(
    mut transaction: &mut Transaction<'a>,
    fqdn: &Fqdn,
    incoming_devices: &Devices,
    db_device_hosts: &DeviceHosts,
) -> Result<(), ImlDevicesError> {
    let (zpools, datasets, volume_groups, logical_volumes) = incoming_devices.values().fold(
        (vec![], vec![], vec![], vec![]),
        |(mut zpools, mut datasets, mut volume_groups, mut logical_volumes), d| {
            match d.device_type {
                DeviceType::Zpool => {
                    zpools.push(d);
                }
                DeviceType::Dataset => {
                    datasets.push(d);
                }
                DeviceType::VolumeGroup => {
                    volume_groups.push(d);
                }
                DeviceType::LogicalVolume => {
                    logical_volumes.push(d);
                }
                _ => {}
            };

            (zpools, datasets, volume_groups, logical_volumes)
        },
    );

    zpools.iter().fold(HashMap::new(), |hm, pool| hm);

    for pool in zpools {
        // Create a map of hostid to device.

        for id in pool.parents.iter() {
            let other_hosts: Vec<_> = filter_device_hosts(&id, &db_device_hosts)
                .filter(|(_, v)| &v.fqdn != fqdn)
                .map(|(_, v)| v)
                .collect();
        }
    }

    Ok(())
}

// pub async fn perform_updates<'a>(
//     mut transaction: &mut Transaction<'a>,
//     fqdn: Fqdn,
//     dhs: DeviceHosts,
//     devices: Devices,
//     db_dhs: DeviceHosts,
//     db_devices: Devices,
// ) -> Result<(), ImlDevicesError> {
//     let local_dhs = get_local_device_hosts(&db_dhs, &fqdn);

//     let other_hosts: Vec<_> = db_dhs
//         .values()
//         .filter(|x| x.fqdn != fqdn)
//         .filter(|x| !x.local)
//         .collect();

//     let dhs_changes = change::get_changes(&local_dhs.iter().collect(), &dhs.iter().collect())
//         .into_iter()
//         .collect::<Vec<_>>();

//     let remote_dhs_changes: Vec<Change<DeviceHostKey>> = other_hosts
//         .iter()
//         .filter(|x| {
//             local_dhs
//                 .iter()
//                 .find(|(_, v)| x.device_id == v.device_id)
//                 .is_some()
//         })
//         .fold(vec![], |mut acc, x| {
//             let change = dhs_changes.iter().find(|&y| y.0 == x.device_id);

//             if let Some(change) = change {
//                 match change {
//                     Change::Add(v) => tracing::warn!(
//                         "Unexepected Add when comparing {:?} (remote) with {:?} (local)",
//                         x,
//                         v
//                     ),
//                     Change::Update(v) => acc.push(Change::Update((v.0.clone(), x.fqdn.clone()))),
//                     Change::Remove(v) => acc.push(Change::Remove((v.0.clone(), x.fqdn.clone()))),
//                 }
//             }

//             acc
//         });

//     let device_changes =
//         change::get_changes(&db_devices.iter().collect(), &devices.iter().collect());

//     // 3. Find any new non-local devices and ensure they are present on all relevant nodes.
//     let remote_dhs_changes = device_changes
//         .iter()
//         .filter(|x| x.is_add())
//         .filter_map(|x| devices.get(x))
//         .fold(remote_dhs_changes, |mut acc, x| {
//             for (fqdn, ys) in db_dhs.iter() {
//                 if x.parents
//                     .iter()
//                     .collect::<BTreeSet<&DeviceId>>()
//                     .is_subset(&ys.keys().collect())
//                 {
//                     acc.push(Change::Add((fqdn.clone(), x.id.clone())));
//                 }
//             }

//             acc
//         });

//     // 4. Insert changes into the DB
//     for c in remote_dhs_changes {
//         match c {
//             Change::Add((fqdn, id)) => {
//                 tracing::info!("Going to insert new remote devicehost {:?}, {:?}", fqdn, id);

//                 let x = dhs.get(&id).unwrap();

//                 insert_device_host(&mut transaction, &fqdn, x).await?;
//             }
//             Change::Update((fqdn, id)) => {
//                 tracing::info!("Going to update remote devicehost {:?}, {:?}", fqdn, id);

//                 let x = dhs.get(&id).unwrap();

//                 update_device_host(&mut transaction, &fqdn, x).await?;
//             }
//             Change::Remove((fqdn, id)) => {
//                 tracing::info!("Going to delete remote devicehost {:?}, {:?}", fqdn, id);

//                 remove_device_host(&mut transaction, &fqdn, &id).await?;
//             }
//         }
//     }

//     Ok(())
// }

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
