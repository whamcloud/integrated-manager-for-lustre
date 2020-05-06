// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod util;

use util::{
    children, children_mut, children_owned, compare_selected_fields, is_virtual, to_display,
};

use device_types::devices::{
    Dataset, Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup, Zpool,
};
use diesel::{self, pg::upsert::excluded, prelude::*};
use im::OrdSet;
use iml_orm::{
    models::{ChromaCoreDevice, NewChromaCoreDevice},
    schema::chroma_core_device::{self, fqdn, table},
    tokio_diesel::*,
    DbPool,
};
use iml_wire_types::Fqdn;
use std::collections;

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

    for (f, d) in devices2 {
        let dd = insert_virtual_devices(d, &parents);

        results.push((f, dd));
    }

    results
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

// This function accepts ownership of `Device` to be able to reconstruct
// its `children`, which is an `OrdSet`.
// `OrdSet` doesn't have `iter_mut` so iterating `children` and mutating them in-place isn't possible.
fn insert_virtual_devices(mut d: Device, parents: &collections::HashSet<Device>) -> Device {
    for p in parents {
        d = insert(d, &p);
    }
    d
}

// This function in only for deduplication of `else` branch in `insert`
fn new_children(d: Device, to_insert: &Device) -> OrdSet<Device> {
    children_owned(d)
        .into_iter()
        .map(|c| insert(c, to_insert))
        .collect()
}

fn insert(mut d: Device, to_insert: &Device) -> Device {
    if compare_selected_fields(&d, to_insert) {
        tracing::debug!(
            "Inserting device {} children to {}",
            to_display(to_insert),
            to_display(&d)
        );

        children_mut(&mut d).map(|x| {
            children(to_insert).map(|y| {
                *x = y.clone();
            })
        });

        d
    } else {
        let d_2 = d.clone();

        match d {
            Device::Root(dd) => Device::Root(Root {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::ScsiDevice(dd) => Device::ScsiDevice(ScsiDevice {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::Partition(dd) => Device::Partition(Partition {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::MdRaid(dd) => Device::MdRaid(MdRaid {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::Mpath(dd) => Device::Mpath(Mpath {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::VolumeGroup(dd) => Device::VolumeGroup(VolumeGroup {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::LogicalVolume(dd) => Device::LogicalVolume(LogicalVolume {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::Zpool(dd) => Device::Zpool(Zpool {
                children: new_children(d_2, to_insert),
                ..dd
            }),
            Device::Dataset(dd) => Device::Dataset(Dataset { ..dd }),
        }
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
