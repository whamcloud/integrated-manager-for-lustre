// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod util;

use util::{
    check_id, children, children_mut, children_owned, compare_by_id, get_id, is_virtual, to_display,
};

use collections::HashMap;
use device_types::{
    devices::{
        Dataset, Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup,
        Zpool,
    },
    zed::PoolCommand,
    Command,
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

pub async fn get_all_devices(pool: &DbPool) -> Vec<(Fqdn, Device)> {
    let all_devices = table
        .load_async::<ChromaCoreDevice>(&pool)
        .await
        .expect("Error getting devices from other hosts");

    all_devices
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

pub fn update_virtual_devices(
    incoming_devices: Vec<(Fqdn, Device)>,
    resolved_devices: Vec<(Fqdn, Device)>,
    commands: &[Command],
) -> Vec<(Fqdn, Device)> {
    let mut results = vec![];

    // As there are multipath devices and we don't compare major, minor, devpath, paths fields,
    // there will be duplicates, of which we'll end up using only one,
    // since when inserting we again search using same fields.
    // So keep parents in a set to avoid iterating the same devices in insert_virtual_devices twice.
    let mut actions = collections::HashSet::new();
    let changes = transform_commands_to_changes(commands);
    tracing::debug!("Changes: {:?}", changes);

    let len = incoming_devices.len();
    tracing::debug!("{} devices", len);

    for (i, (f, d)) in incoming_devices.iter().enumerate() {
        let mut aa = collect_actions(&d, 0, None, &changes);
        for (_, c) in changes.iter() {
            match c {
                Change::Remove(id) => aa.push(Action::Remove(id.clone())),
                _ => {}
            }
        }

        tracing::debug!("Collect: host: {}, actions: {:?}", f, actions);

        tracing::info!(
            "Collected {:3} actions at {:25} host",
            aa.len(),
            f.to_string(),
        );
        actions.extend(aa);
    }

    for (f, d) in resolved_devices {
        tracing::debug!("Apply: host: {}, actions: {:?}", f, actions);

        tracing::info!(
            "Taking {:3} actions at {:25} host",
            actions.len(),
            f.to_string(),
        );
        let dd = process_actions(d, &mut actions).unwrap();

        results.push((f, dd));
    }

    results
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub(crate) enum Id {
    ScsiDeviceSerial(String),
    PartitionSerial(String),
    MdRaidUuid(String),
    MpathSerial(String),
    VolumeGroupUuid(String),
    LogicalVolumeUuid(String),
    ZpoolGuid(u64),
    DatasetGuid(u64),
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
enum Change {
    Upsert(Id),
    Remove(Id),
}

type ChangesMap = HashMap<Id, Change>;

fn transform_commands_to_changes(commands: &[Command]) -> ChangesMap {
    let mut results = HashMap::new();

    for c in commands {
        match c {
            Command::PoolCommand(pc) => {
                tracing::info!("Got PoolCommand");
                match pc {
                    PoolCommand::UpdatePool(p) => {
                        tracing::info!("Got UpdatePool");

                        let guid = p.guid;
                        results.insert(Id::ZpoolGuid(guid), Change::Upsert(Id::ZpoolGuid(guid)));
                    }
                    PoolCommand::RemovePool(guid) => {
                        tracing::info!("Got RemovePool");

                        tracing::info!("Trying to parse guid {}", guid.0);
                        // FIXME: Remove [2..]
                        let guid = u64::from_str_radix(&guid.0[2..], 16).unwrap();
                        results.insert(Id::ZpoolGuid(guid), Change::Remove(Id::ZpoolGuid(guid)));
                    }
                    _ => {}
                }
            }
            _ => {}
        }
    }

    results
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
enum IdentifiedDevice<'d> {
    Parent(&'d Device),
    Itself(&'d Device),
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
enum Action<'d> {
    Upsert(IdentifiedDevice<'d>),
    Remove(Id),
}

fn collect_actions<'d>(
    d: &'d Device,
    level: usize,
    parent: Option<&'d Device>,
    changes: &ChangesMap,
) -> Vec<Action<'d>> {
    let mut results = vec![];
    tracing::debug!("Inspecting {}", to_display(&d));

    if changes.is_empty() {
        return results;
    }

    // FIXME: Remove Change::Remove handling on encountering a device

    match d {
        Device::Root(dd) => {
            for c in dd.children.iter() {
                results.extend(collect_actions(c, level + 1, Some(d), changes));
            }
            results
        }
        Device::ScsiDevice(dd) => {
            for c in dd.children.iter() {
                results.extend(collect_actions(c, level + 1, Some(d), changes));
            }
            results
        }
        Device::Partition(dd) => {
            for c in dd.children.iter() {
                results.extend(collect_actions(c, level + 1, Some(d), changes));
            }
            results
        }
        Device::Mpath(dd) => {
            for c in dd.children.iter() {
                results.extend(collect_actions(c, level + 1, Some(d), changes));
            }
            results
        }
        Device::MdRaid(dd) => {
            let maybe_id = get_id(d);
            let maybe_change = maybe_id.map(|id| changes.get(&id)).flatten();
            match maybe_change {
                Some(Change::Upsert(id)) => {
                    tracing::info!("Saving Upsert");
                    results.push(Action::Upsert(IdentifiedDevice::Parent(parent.expect(
                        "Tried to push to parents the parent of the Root, which doesn't exist",
                    ))));
                }
                Some(Change::Remove(id)) => {
                    tracing::info!("Saving Remove");
                    results.push(Action::Remove(id.clone()));
                }
                None => {
                    for c in dd.children.iter() {
                        results.extend(collect_actions(c, level + 1, Some(d), changes));
                    }
                }
            }
            results
        }
        Device::LogicalVolume(dd) => {
            let maybe_id = get_id(d);
            let maybe_change = maybe_id.map(|id| changes.get(&id)).flatten();
            match maybe_change {
                Some(Change::Upsert(id)) => {
                    tracing::info!("Saving Upsert");
                    results.push(Action::Upsert(IdentifiedDevice::Parent(parent.expect(
                        "Tried to push to parents the parent of the Root, which doesn't exist",
                    ))));
                }
                Some(Change::Remove(id)) => {
                    tracing::info!("Saving Remove");
                    results.push(Action::Remove(id.clone()));
                }
                None => {
                    for c in dd.children.iter() {
                        results.extend(collect_actions(c, level + 1, Some(d), changes));
                    }
                }
            }
            results
        }
        Device::VolumeGroup(dd) => {
            let maybe_id = get_id(d);
            let maybe_change = maybe_id.map(|id| changes.get(&id)).flatten();
            match maybe_change {
                Some(Change::Upsert(id)) => {
                    tracing::info!("Saving Upsert");
                    results.push(Action::Upsert(IdentifiedDevice::Parent(parent.expect(
                        "Tried to push to parents the parent of the Root, which doesn't exist",
                    ))));
                }
                Some(Change::Remove(id)) => {
                    tracing::info!("Saving Remove");
                    results.push(Action::Remove(id.clone()));
                }
                None => {
                    for c in dd.children.iter() {
                        results.extend(collect_actions(c, level + 1, Some(d), changes));
                    }
                }
            }
            results
        }
        Device::Zpool(dd) => {
            let maybe_id = get_id(d);
            let maybe_change = maybe_id.map(|id| changes.get(&id)).flatten();
            match maybe_change {
                Some(Change::Upsert(id)) => {
                    tracing::info!("Saving Upsert");
                    results.push(Action::Upsert(IdentifiedDevice::Parent(parent.expect(
                        "Tried to push to parents the parent of the Root, which doesn't exist",
                    ))));
                }
                Some(Change::Remove(id)) => {
                    tracing::info!("Saving Remove");
                    results.push(Action::Remove(id.clone()));
                }
                None => {
                    for c in dd.children.iter() {
                        results.extend(collect_actions(c, level + 1, Some(d), changes));
                    }
                }
            }
            results
        }
        Device::Dataset(dd) => {
            let maybe_id = get_id(d);
            let maybe_change = maybe_id.map(|id| changes.get(&id)).flatten();
            match maybe_change {
                Some(Change::Upsert(id)) => {
                    tracing::info!("Saving Upsert");
                    results.push(Action::Upsert(IdentifiedDevice::Parent(parent.expect(
                        "Tried to push to parents the parent of the Root, which doesn't exist",
                    ))));
                }
                Some(Change::Remove(id)) => {
                    tracing::info!("Saving Remove");
                    results.push(Action::Remove(id.clone()));
                }
                None => {
                    // No children possible
                }
            }
            results
        }
        _ => results,
    }
}

// Returns `true` if action was applied
fn maybe_apply_action(mut d: Device, action: &Action) -> (Option<Device>, bool) {
    match action {
        Action::Upsert(device) => match device {
            IdentifiedDevice::Parent(new_d) => {
                if compare_by_id(&d, new_d) {
                    tracing::debug!(
                        "Inserting device {} children to {}",
                        to_display(new_d),
                        to_display(&d)
                    );

                    children_mut(&mut d).map(|x| {
                        children(new_d).map(|y| {
                            *x = y.clone();
                        })
                    });

                    (Some(d), true)
                } else {
                    (Some(d), false)
                }
            }
            _ => (Some(d), false),
        },
        Action::Remove(id) => match id {
            Id::ZpoolGuid(guid) => {
                if check_id(&d, id) {
                    (None, true)
                } else {
                    (Some(d), false)
                }
            }
            _ => (Some(d), false),
        },
    }
}

// This function accepts ownership of `Device` to be able to reconstruct
// its `children`, which is an `OrdSet`, inside of `insert`.
// `OrdSet` doesn't have `iter_mut` so iterating `children` and mutating them in-place isn't possible.
fn process_actions(mut d: Device, actions: &mut collections::HashSet<Action>) -> Option<Device> {
    tracing::debug!("Processing {}", to_display(&d));
    let mut actions_to_remove = collections::HashSet::new();
    let mut this_device_is_removed = false;
    for a in actions.iter() {
        let (new_d, did_apply) = maybe_apply_action(d.clone(), a);
        if did_apply {
            actions_to_remove.insert(a.clone());
        }
        if let Some(new_d) = new_d {
            d = new_d;
        } else {
            this_device_is_removed = true;
        }
    }
    if !actions_to_remove.is_empty() {
        tracing::info!("Took {} actions", actions_to_remove.len());
    }
    // FIXME: We can't remove action right after taking it once, since we have multipath devices which
    // resolve to devices with same ids. That means we'll encounter a matching device more than once
    // for a in actions_to_remove {
    //     assert!(actions.remove(&a));
    // }
    if this_device_is_removed {
        tracing::debug!("Removing {}", to_display(&d));
        return None;
    } else if actions.is_empty() {
        return Some(d);
    } else {
        let d_2 = d.clone();

        Some(match d {
            Device::Root(dd) => Device::Root(Root {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::ScsiDevice(dd) => Device::ScsiDevice(ScsiDevice {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::Partition(dd) => Device::Partition(Partition {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::MdRaid(dd) => Device::MdRaid(MdRaid {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::Mpath(dd) => Device::Mpath(Mpath {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::VolumeGroup(dd) => Device::VolumeGroup(VolumeGroup {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::LogicalVolume(dd) => Device::LogicalVolume(LogicalVolume {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::Zpool(dd) => Device::Zpool(Zpool {
                children: new_children(d_2, actions),
                ..dd
            }),
            Device::Dataset(dd) => Device::Dataset(Dataset { ..dd }),
        })
    }
}

// This function in only for deduplication of `else` branch in `insert`
fn new_children(d: Device, actions: &mut collections::HashSet<Action>) -> OrdSet<Device> {
    children_owned(d)
        .into_iter()
        .filter_map(|c| process_actions(c, actions))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use device_types::Output;
    use insta::assert_json_snapshot;
    use std::{fs, rc::Rc};
    use test_case::test_case;

    fn init_subscriber() {
        if let Ok(o) = std::env::var("ENABLE_LOG") {
            if o == "1" {
                tracing_subscriber::fmt::init();
            }
        }
    }

    fn deser_fixture(path1: &str, path2: &str, fqdn1: Fqdn, fqdn2: Fqdn) -> Vec<(Fqdn, Device)> {
        let device1 = fs::read_to_string(path1).unwrap();
        let device1: Device = serde_json::from_str(&device1).unwrap();

        let device2 = fs::read_to_string(path2).unwrap();
        let device2: Device = serde_json::from_str(&device2).unwrap();

        vec![(fqdn1, device1), (fqdn2, device2)]
    }

    fn deser_fixture_2(paths: &[&str], fqdns: &[Fqdn]) -> Vec<(Fqdn, (Device, Vec<Command>))> {
        let mut results = vec![];

        for (p, f) in paths.iter().zip(fqdns) {
            let output = fs::read_to_string(p).unwrap();
            let o: (Device, Vec<Command>) = serde_json::from_str(&output).unwrap();

            results.push((f.clone(), o));
        }

        results
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

    #[test_case(
        "simple_test",
        "fixtures/device-mds1.local-2034-pruned.json",
        "fixtures/device-mds2.local-2033-pruned.json",
        "mds1.local",
        "mds2.local"
    )]
    #[test_case(
        "full_mds_test",
        "fixtures/device-mds1.local-2034.json",
        "fixtures/device-mds2.local-2033.json",
        "mds1.local",
        "mds2.local"
    )]
    #[test_case(
        "full_oss_test",
        "fixtures/device-oss1.local-62.json",
        "fixtures/device-oss2.local-61.json",
        "oss1.local",
        "oss2.local"
    )]
    fn test(test_name: &str, path1: &str, path2: &str, fqdn1: &str, fqdn2: &str) {
        init_subscriber();

        let devices = deser_fixture(path1, path2, Fqdn(fqdn1.into()), Fqdn(fqdn2.into()));

        let results = update_virtual_devices(devices, Vec::new(), &Vec::new());

        compare_results(results, test_name);
    }

    #[test_case(
        "simple_commands_test",
        &[
            "fixtures/output-mds2.local-8-pruned.json",
            "fixtures/output-mds1.local-9-pruned.json",
            "fixtures/output-mds2.local-10-pruned.json",
        ],
        &[   
            "mds2.local",
            "mds1.local",
            "mds2.local"
        ]
    )]
    fn test_2(test_name: &str, paths: &[&str], fqdns: &[&str]) {
        init_subscriber();

        let fqdns: Vec<Fqdn> = fqdns.into_iter().map(|s| Fqdn(s.to_string())).collect();
        let outputs = deser_fixture_2(paths, &fqdns);

        let mut incoming_devices = vec![];
        let mut resolved_devices = vec![];

        for (f, o) in outputs {
            tracing::info!("Handling {}", f.to_string());
            let (d, cs) = o;
            incoming_devices.push((f, d));
            let incoming_devices_2 = incoming_devices.clone();
            let resolved_devices_2 = incoming_devices.clone();
            let results = update_virtual_devices(incoming_devices_2, resolved_devices_2, &cs);

            compare_results(results.clone(), test_name);

            std::mem::replace(&mut resolved_devices, results);
        }
    }
}
