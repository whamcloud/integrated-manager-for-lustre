// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::devices::{
    Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup, Zpool,
};
use diesel::{self, pg::upsert::excluded, prelude::*};
use im::{HashSet, OrdSet};

use iml_orm::{
    models::{ChromaCoreDevice, NewChromaCoreDevice},
    schema::chroma_core_device::{self, fqdn, table},
    tokio_diesel::*,
    DbPool,
};

use iml_wire_types::Fqdn;
use std::path::PathBuf;

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

        tracing::info!("Inserted other device from host {}", new_device.fqdn);
        tracing::trace!("Inserted other device {:?}", new_device);
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

pub async fn update_virtual_devices(devices: Vec<(Fqdn, Device)>) -> Vec<(Fqdn, Device)> {
    let mut results = vec![];
    let mut parents = vec![];
    let devices2 = devices.clone();

    for (f, d) in devices {
        let ps = collect_virtual_device_parents(&d, 0, None);
        tracing::info!("Collected {} parents at {} host", ps.len(), f.to_string());
        parents.extend(ps);
    }

    // TODO: Assert that all parents are distinct
    for (ff, mut dd) in devices2 {
        insert_virtual_devices(&mut dd, &parents);

        results.push((ff, dd));
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
        tracing::info!(
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

fn insert(d: &mut Device, to_insert: &Device) {
    if compare_selected_fields(d, to_insert) {
        tracing::info!(
            "Inserting a device {} to {}",
            to_display(to_insert),
            to_display(d)
        );
        *d = to_insert.clone();
    } else {
        match d {
            Device::Root(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::ScsiDevice(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::Partition(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::MdRaid(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::Mpath(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::VolumeGroup(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::LogicalVolume(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::Zpool(d) => {
                for mut c in d.children.iter_mut() {
                    insert(&mut c, to_insert);
                }
            }
            Device::Dataset(_) => {}
        }
    }
}

fn selected_fields(d: &Device) -> Device {
    match d {
        Device::Root(d) => Device::Root(Root {
            children: HashSet::new(),
            ..d.clone()
        }),
        Device::ScsiDevice(d) => Device::ScsiDevice(ScsiDevice {
            children: HashSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Partition(d) => Device::Partition(Partition {
            children: HashSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::MdRaid(d) => Device::MdRaid(MdRaid {
            children: HashSet::new(),
            major: String::new(),
            minor: String::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Mpath(d) => Device::Mpath(Mpath {
            children: HashSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::VolumeGroup(d) => Device::VolumeGroup(VolumeGroup {
            children: HashSet::new(),
            ..d.clone()
        }),
        Device::LogicalVolume(d) => Device::LogicalVolume(LogicalVolume {
            children: HashSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Zpool(d) => Device::Zpool(Zpool {
            children: HashSet::new(),
            ..d.clone()
        }),
        Device::Dataset(d) => Device::Dataset(d.clone()),
    }
}

fn compare_selected_fields(a: &Device, b: &Device) -> bool {
    selected_fields(a) == selected_fields(b)
}

fn insert_virtual_devices(d: &mut Device, parents: &[Device]) {
    for p in parents {
        insert(d, &p);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_json_snapshot;
    use jsondata;
    use std::fs;

    #[tokio::test]
    async fn simple_test() {
        let path1 = "fixtures/device-mds1.local-2034-pruned.json";
        let path2 = "fixtures/device-mds2.local-2033-pruned.json";

        let device1 = fs::read_to_string(path1).unwrap();
        let device1: Device = serde_json::from_str(&device1).unwrap();

        let device2 = fs::read_to_string(path2).unwrap();
        let device2: Device = serde_json::from_str(&device2).unwrap();

        let devices = vec![
            (Fqdn("mds1.local".into()), device1),
            (Fqdn("mds2.local".into()), device2),
        ];

        let results = update_virtual_devices(devices).await;

        for (f, d) in results {
            let mut children = vec![];
            match d {
                Device::Root(dd) => {
                    for c in dd.children {
                        children.push(c.clone());
                    }
                }
                _ => unreachable!(),
            }

            let mut children_ordered = vec![];
            for c in children {
                let c_string = serde_json::to_string(&c).unwrap();

                let c_ordered = c_string.parse::<jsondata::Json>().unwrap();

                children_ordered.push(c_ordered);
            }

            children_ordered.sort();

            for (i, c) in children_ordered.iter().enumerate() {
                let c_string = c.to_string();
                let c_serde: serde_json::Value = serde_json::from_str(&c_string).unwrap();
                assert_json_snapshot!(format!("simple_test_{}_{}", f, i), c_serde);
            }
        }
    }

    #[tokio::test]
    async fn full_mds_test() {
        let path1 = "fixtures/device-mds1.local-2034.json";
        let path2 = "fixtures/device-mds2.local-2033.json";

        let device1 = fs::read_to_string(path1).unwrap();
        let device1: Device = serde_json::from_str(&device1).unwrap();

        let device2 = fs::read_to_string(path2).unwrap();
        let device2: Device = serde_json::from_str(&device2).unwrap();

        let devices = vec![
            (Fqdn("mds1.local".into()), device1),
            (Fqdn("mds2.local".into()), device2),
        ];

        let results = update_virtual_devices(devices).await;

        for (f, d) in results {
            let mut children = vec![];
            match d {
                Device::Root(dd) => {
                    for c in dd.children {
                        children.push(c.clone());
                    }
                }
                _ => unreachable!(),
            }

            let mut children_ordered = vec![];
            for c in children {
                let c_string = serde_json::to_string(&c).unwrap();

                let c_ordered = c_string.parse::<jsondata::Json>().unwrap();

                children_ordered.push(c_ordered);
            }

            children_ordered.sort();

            for (i, c) in children_ordered.iter().enumerate() {
                let c_string = c.to_string();
                let c_serde: serde_json::Value = serde_json::from_str(&c_string).unwrap();
                assert_json_snapshot!(format!("full_mds_test_{}_{}", f, i), c_serde);
            }
        }
    }

    #[tokio::test]
    async fn full_oss_test() {
        let path1 = "fixtures/device-oss1.local-2036.json";
        let path2 = "fixtures/device-oss2.local-2035.json";

        let device1 = fs::read_to_string(path1).unwrap();
        let device1: Device = serde_json::from_str(&device1).unwrap();

        let device2 = fs::read_to_string(path2).unwrap();
        let device2: Device = serde_json::from_str(&device2).unwrap();

        let devices = vec![
            (Fqdn("oss1.local".into()), device1),
            (Fqdn("oss2.local".into()), device2),
        ];

        let results = update_virtual_devices(devices).await;

        for (f, d) in results {
            let mut children = vec![];
            match d {
                Device::Root(dd) => {
                    for c in dd.children {
                        children.push(c.clone());
                    }
                }
                _ => unreachable!(),
            }

            let mut children_ordered = vec![];
            for c in children {
                let c_string = serde_json::to_string(&c).unwrap();

                let c_ordered = c_string.parse::<jsondata::Json>().unwrap();

                children_ordered.push(c_ordered);
            }

            children_ordered.sort();

            for (i, c) in children_ordered.iter().enumerate() {
                let c_string = c.to_string();
                let c_serde: serde_json::Value = serde_json::from_str(&c_string).unwrap();
                assert_json_snapshot!(format!("full_oss_test_{}_{}", f, i), c_serde);
            }
        }
    }
}
