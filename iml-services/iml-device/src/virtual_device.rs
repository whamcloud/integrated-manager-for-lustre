// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::devices::{
    Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup, Zpool,
};
use diesel::{self, pg::upsert::excluded, prelude::*};
use im::{HashSet, OrdSet, Vector};

use iml_orm::{
    models::{ChromaCoreDevice, NewChromaCoreDevice},
    schema::chroma_core_device::{self, fqdn, table},
    tokio_diesel::*,
    DbPool,
};

use iml_wire_types::Fqdn;
use std::{collections, mem, path::PathBuf};

pub async fn save_devices(devices: Vec<(Fqdn, Device)>, pool: &DbPool) {
    for (f, d) in devices.into_iter() {
        let device_to_insert = NewChromaCoreDevice {
            fqdn: f.to_string(),
            devices: serde_json::to_value(d).expect("Could not convert other Device to JSON."),
        };

        let new_device = diesel::insert_into(table)
            .values(device_to_insert)
            .on_conflict(fqdn)
            .do_update()
            .set(chroma_core_device::devices.eq(excluded(chroma_core_device::devices)))
            .get_result_async::<ChromaCoreDevice>(pool)
            .await
            .expect("Error saving new device");

        tracing::info!("Inserted devices from host {}", new_device.fqdn);
        tracing::trace!("Inserted devices {:?}", new_device);
    }
}

pub async fn get_other_devices(f: &Fqdn, pool: &DbPool) -> Vec<(Fqdn, Device)> {
    let other_devices = table
        .filter(fqdn.ne(f.to_string()))
        .load_async::<ChromaCoreDevice>(&pool)
        .await
        .expect("Error getting devices from other hosts");

    other_devices
        .into_iter()
        .map(|d| {
            (
                Fqdn(d.fqdn),
                serde_json::from_value(d.devices)
                    .expect("Couldn't deserialize Device from JSON when reading from DB"),
            )
        })
        .collect()
}

pub fn update_virtual_devices(devices: Vec<(Fqdn, Device)>) -> Vec<(Fqdn, Device)> {
    let mut results = vec![];

    // As there are multipath devices and we don't compare major, minor, devpath, paths fields,
    // there will be duplicates, of which we'll end up using only one,
    // since when inserting we again search using same fields.
    // So keep parents in a set to avoid iterating the same devices in insert_virtual_devices twice.
    let mut parents = collections::HashSet::new();
    let devices2 = devices.clone();

    for (f, d) in devices {
        let ps = collect_virtual_device_parents(&d, 0, None);
        tracing::info!("Collected {} parents at {} host", ps.len(), f.to_string());
        parents.extend(ps);
    }

    for (f, mut d) in devices2 {
        insert_virtual_devices(&mut d, &parents);

        results.push((f, d));
    }

    results
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

fn to_display(d: &Device) -> String {
    match d {
        Device::Root(d) => format!("Root: children: {}", d.children.len()),
        Device::ScsiDevice(ref d) => format!(
            "ScsiDevice: serial: {}, children: {}",
            d.serial.as_ref().unwrap_or(&"None".into()),
            d.children.len()
        ),
        Device::Partition(d) => format!(
            "Partition: serial: {}, children: {}",
            d.serial.as_ref().unwrap_or(&"None".into()),
            d.children.len()
        ),
        Device::MdRaid(d) => format!("MdRaid: uuid: {}, children: {}", d.uuid, d.children.len()),
        Device::Mpath(d) => format!(
            "Mpath: serial: {}, children: {}",
            d.serial.as_ref().unwrap_or(&"None".into()),
            d.children.len(),
        ),
        Device::VolumeGroup(d) => format!(
            "VolumeGroup: name: {}, children: {}",
            d.name,
            d.children.len()
        ),
        Device::LogicalVolume(d) => format!(
            "LogicalVolume: uuid: {}, children: {}",
            d.uuid,
            d.children.len()
        ),
        Device::Zpool(d) => format!("Zpool: guid: {}, children: {}", d.guid, d.children.len()),
        Device::Dataset(d) => format!("Dataset: guid: {}, children: 0", d.guid),
    }
}

fn collect_virtual_device_parents(
    d: &Device,
    level: usize,
    parent: Option<&Device>,
) -> Vec<Device> {
    let mut results = vec![];

    if is_virtual(d) {
        tracing::debug!(
            "Collecting parent {} of {}",
            parent.map(|x| to_display(x)).unwrap_or("None".into()),
            to_display(d)
        );
        vec![parent
            .expect("Tried to push to parents the parent of the Root, which doesn't exist")
            .clone()]
    } else {
        match d {
            Device::Root(dd) => {
                for c in dd.children.iter() {
                    results.extend(collect_virtual_device_parents(c, level + 1, Some(d)));
                }
                results
            }
            Device::ScsiDevice(dd) => {
                for c in dd.children.iter() {
                    results.extend(collect_virtual_device_parents(c, level + 1, Some(d)));
                }
                results
            }
            Device::Partition(dd) => {
                for c in dd.children.iter() {
                    results.extend(collect_virtual_device_parents(c, level + 1, Some(d)));
                }
                results
            }
            Device::Mpath(dd) => {
                for c in dd.children.iter() {
                    results.extend(collect_virtual_device_parents(c, level + 1, Some(d)));
                }
                results
            }
            _ => vec![],
        }
    }
}

fn children_mut(d: &mut Device) -> Option<&mut Vector<Device>> {
    match d {
        Device::Root(dd) => Some(&mut dd.children),
        Device::ScsiDevice(dd) => Some(&mut dd.children),
        Device::Partition(dd) => Some(&mut dd.children),
        Device::MdRaid(dd) => Some(&mut dd.children),
        Device::Mpath(dd) => Some(&mut dd.children),
        Device::VolumeGroup(dd) => Some(&mut dd.children),
        Device::LogicalVolume(dd) => Some(&mut dd.children),
        Device::Zpool(dd) => Some(&mut dd.children),
        Device::Dataset(_) => None,
    }
}

fn children(d: &Device) -> Option<&Vector<Device>> {
    match d {
        Device::Root(dd) => Some(&dd.children),
        Device::ScsiDevice(dd) => Some(&dd.children),
        Device::Partition(dd) => Some(&dd.children),
        Device::MdRaid(dd) => Some(&dd.children),
        Device::Mpath(dd) => Some(&dd.children),
        Device::VolumeGroup(dd) => Some(&dd.children),
        Device::LogicalVolume(dd) => Some(&dd.children),
        Device::Zpool(dd) => Some(&dd.children),
        Device::Dataset(_) => None,
    }
}

fn insert(mut d: &mut Device, to_insert: &Device) {
    if compare_selected_fields(d, to_insert) {
        tracing::debug!(
            "Inserting device {} children to {}",
            to_display(to_insert),
            to_display(d)
        );

        children_mut(&mut d).map(|x| {
            children(to_insert).map(|y| {
                *x = y.clone();
            })
        });
    } else {
        children_mut(d).map(|cc| {
            for mut c in cc.iter_mut() {
                insert(&mut c, to_insert);
            }
        });
    }
}

fn selected_fields(d: &Device) -> Device {
    match d {
        Device::Root(d) => Device::Root(Root {
            children: Vector::new(),
            ..d.clone()
        }),
        Device::ScsiDevice(d) => Device::ScsiDevice(ScsiDevice {
            children: Vector::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Partition(d) => Device::Partition(Partition {
            children: Vector::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::MdRaid(d) => Device::MdRaid(MdRaid {
            children: Vector::new(),
            major: String::new(),
            minor: String::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Mpath(d) => Device::Mpath(Mpath {
            children: Vector::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::VolumeGroup(d) => Device::VolumeGroup(VolumeGroup {
            children: Vector::new(),
            ..d.clone()
        }),
        Device::LogicalVolume(d) => Device::LogicalVolume(LogicalVolume {
            children: Vector::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Zpool(d) => Device::Zpool(Zpool {
            children: Vector::new(),
            ..d.clone()
        }),
        Device::Dataset(d) => Device::Dataset(d.clone()),
    }
}

fn compare_selected_fields(a: &Device, b: &Device) -> bool {
    selected_fields(a) == selected_fields(b)
}

fn insert_virtual_devices(d: &mut Device, parents: &collections::HashSet<Device>) {
    for p in parents {
        insert(d, &p);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_json_snapshot;
    use std::fs;

    fn deser_fixture(path1: &str, path2: &str, fqdn1: Fqdn, fqdn2: Fqdn) -> Vec<(Fqdn, Device)> {
        let device1 = fs::read_to_string(path1).unwrap();
        let device1: Device = serde_json::from_str(&device1).unwrap();

        let device2 = fs::read_to_string(path2).unwrap();
        let device2: Device = serde_json::from_str(&device2).unwrap();

        vec![(fqdn1, device1), (fqdn2, device2)]
    }

    // This function gets top-level children and snapshots them one-by-one.
    // This way you can compare i.e.
    // snapshots/iml_device__virtual_device__tests__full_mds_test_mds1.local_0.snap
    // and
    // snapshots/iml_device__virtual_device__tests__full_mds_test_mds2.local_0.snap
    // and find those are the same modulo devpath, paths, major, minor fields.
    fn compare_results(results: Vec<(Fqdn, Device)>, test_name: &str) {
        for (f, d) in results {
            let mut children = vec![];
            match d {
                Device::Root(dd) => {
                    for c in dd.children {
                        children.push(c);
                    }
                }
                _ => unreachable!(),
            }

            for (i, c) in children.iter().enumerate() {
                assert_json_snapshot!(format!("{}_{}_{}", test_name, f, i), c);
            }
        }
    }

    #[test]
    fn simple_test() {
        let devices = deser_fixture(
            "fixtures/device-mds1.local-2034-pruned.json",
            "fixtures/device-mds2.local-2033-pruned.json",
            Fqdn("mds1.local".into()),
            Fqdn("mds2.local".into()),
        );

        let results = update_virtual_devices(devices);

        compare_results(results, "simple_test");
    }

    #[test]
    fn full_mds_test() {
        let devices = deser_fixture(
            "fixtures/device-mds1.local-2034.json",
            "fixtures/device-mds2.local-2033.json",
            Fqdn("mds1.local".into()),
            Fqdn("mds2.local".into()),
        );

        let results = update_virtual_devices(devices);

        compare_results(results, "full_mds_test");
    }

    #[test]
    fn full_oss_test() {
        let devices = deser_fixture(
            "fixtures/device-oss1.local-62.json",
            "fixtures/device-oss2.local-61.json",
            Fqdn("oss1.local".into()),
            Fqdn("oss2.local".into()),
        );

        let results = update_virtual_devices(devices);

        compare_results(results, "full_oss_test");
    }
}
