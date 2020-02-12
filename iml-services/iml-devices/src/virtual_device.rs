// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    breadth_first_parent_iterator::BreadthFirstParentIterator,
    change::Change,
    db::{DeviceHosts, Devices},
    error::ImlDevicesError,
};
use iml_wire_types::{
    db::{Device, DeviceHost, DeviceId, DeviceType, MountPath, Paths},
    Fqdn,
};
use itertools::Itertools;
use std::collections::{BTreeMap, BTreeSet};

fn is_virtual_device(device: &Device) -> bool {
    device.device_type == DeviceType::MdRaid
        || device.device_type == DeviceType::VolumeGroup
        || device.device_type == DeviceType::LogicalVolume
        || device.device_type == DeviceType::Dataset
        || device.device_type == DeviceType::Zpool
}

fn make_other_device_host(
    device_id: DeviceId,
    fqdn: Fqdn,
    virtual_device_host: Option<&DeviceHost>,
) -> DeviceHost {
    DeviceHost {
        device_id,
        fqdn,
        local: false,
        paths: Paths(
            virtual_device_host
                .map(|x| x.paths.0.clone())
                .unwrap_or(BTreeSet::new()),
        ),
        mount_path: MountPath(None),
        fs_type: virtual_device_host
            .map(|x| x.fs_type.clone())
            .unwrap_or(None),
        fs_label: virtual_device_host
            .map(|x| x.fs_label.clone())
            .unwrap_or(None),
        fs_uuid: virtual_device_host
            .map(|x| x.fs_uuid.clone())
            .unwrap_or(None),
    }
}

fn make_other_device_host_for_removal(device_id: DeviceId, fqdn: Fqdn) -> DeviceHost {
    DeviceHost {
        device_id,
        fqdn,
        local: false,
        paths: Paths(BTreeSet::new()),
        mount_path: MountPath(None),
        fs_type: None,
        fs_label: None,
        fs_uuid: None,
    }
}

fn add_device_host(
    device_id: DeviceId,
    fqdn: Fqdn,
    virtual_device_host: Option<&DeviceHost>,
    results: &mut BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>,
) {
    let other_device_host =
        make_other_device_host(device_id.clone(), fqdn.clone(), virtual_device_host);

    tracing::info!(
        "Adding new device host with id {:?} to host {:?}",
        device_id,
        fqdn
    );

    results.insert(
        (device_id.clone(), fqdn.clone()),
        Change::Add(other_device_host),
    );
}

fn update_device_host(
    device_id: DeviceId,
    fqdn: Fqdn,
    virtual_device_host: Option<&DeviceHost>,
    results: &mut BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>,
) {
    let other_device_host =
        make_other_device_host(device_id.clone(), fqdn.clone(), virtual_device_host);

    tracing::info!(
        "Updating device host with id {:?} on host {:?}",
        device_id,
        fqdn
    );

    results.insert(
        (device_id.clone(), fqdn.clone()),
        Change::Update(other_device_host),
    );
}

fn remove_device_host(
    device_id: DeviceId,
    fqdn: Fqdn,
    results: &mut BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>,
) {
    let other_device_host = make_other_device_host_for_removal(device_id.clone(), fqdn.clone());

    tracing::info!(
        "Removing device host with id {:?} on host {:?}",
        device_id,
        fqdn,
    );
    results.insert(
        (device_id.clone(), fqdn.clone()),
        Change::Remove(other_device_host),
    );
}

fn are_all_parents_available(
    devices: &Devices,
    device_hosts: &DeviceHosts,
    host: Fqdn,
    child_id: &DeviceId,
) -> bool {
    let mut i = BreadthFirstParentIterator::new(devices, child_id);
    let all_available = i.all(|p| {
        let result = device_hosts.get(&(p.clone(), host.clone())).is_some();
        tracing::trace!("Checking device {:?} on host {:?}: {:?}", p, host, result);
        result
    });
    tracing::info!(
        "are_all_parents_available: host: {:?}, device: {:?}, all_available: {:?}",
        host,
        child_id,
        all_available
    );
    all_available
}

fn are_all_parents_available_with_results(
    devices: &Devices,
    device_hosts: &DeviceHosts,
    results: &BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>,
    host: Fqdn,
    child_id: &DeviceId,
) -> bool {
    let mut i = BreadthFirstParentIterator::new(devices, child_id);
    let all_available = i.all(|p| {
        let result = device_hosts.get(&(p.clone(), host.clone())).is_some();
        tracing::trace!("Checking device {:?} on host {:?}: {:?}", p, host, result);
        let result_results = if !result {
            let result_results = results.get(&(p.clone(), host.clone())).is_some();
            // TODO: Check if the result is not Remove<...>. Probably just assert it.
            tracing::trace!(
                "Checking device {:?} on host {:?} in results: {:?}",
                p,
                host,
                result_results
            );
            Some(result_results)
        } else {
            None
        };

        result || result_results.unwrap()
    });
    tracing::info!(
        "are_all_parents_available_with_results: host: {:?}, device: {:?}, all_available: {:?}",
        host,
        child_id,
        all_available
    );
    all_available
}

pub fn compute_virtual_device_changes<'a>(
    fqdn: &Fqdn,
    incoming_devices: &Devices,
    incoming_device_hosts: &DeviceHosts,
    db_devices: &Devices,
    db_device_hosts: &DeviceHosts,
) -> Result<BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>, ImlDevicesError> {
    tracing::trace!(
        "Incoming: devices: {}, device hosts: {}, Database: devices: {}, device hosts: {}",
        incoming_devices.len(),
        incoming_device_hosts.len(),
        db_devices.len(),
        db_device_hosts.len()
    );
    let mut results = BTreeMap::new();

    let other_device_hosts: DeviceHosts = db_device_hosts
        .iter()
        .filter(|(_, dh)| &dh.fqdn != fqdn)
        .map(|(x, y)| (x.clone(), y.clone()))
        .collect();
    tracing::trace!("other_device_hosts: {:#?}", other_device_hosts);

    let all_device_hosts: DeviceHosts = incoming_device_hosts
        .iter()
        .chain(other_device_hosts.iter())
        .map(|(x, y)| (x.clone(), y.clone()))
        .collect();
    tracing::trace!("all_device_hosts: {:#?}", all_device_hosts);

    // let other_device_hosts_devices: BTreeSet<DeviceId> = all_device_hosts
    //     .iter()
    //     .filter_map(
    //         |((id, host), _)| {
    //             if host != fqdn {
    //                 Some(id.clone())
    //             } else {
    //                 None
    //             }
    //         },
    //     )
    //     .collect();
    // tracing::trace!(
    //     "other_device_hosts_devices: {:#?}",
    //     other_device_hosts_devices
    // );

    let all_devices: Devices = incoming_devices
        .iter()
        .chain(db_devices.iter())
        .filter_map(|(id, d)| Some((id.clone(), d.clone())))
        .collect();
    tracing::trace!("all_devices: {:#?}", all_devices);

    let virtual_devices = all_devices
        .iter()
        .filter(|(_, d)| is_virtual_device(d))
        .map(|(_, d)| d)
        .sorted_by_key(|d| d.max_depth);

    tracing::trace!("virtual_devices: {:#?}", virtual_devices);

    // We're sorting the devices by depth
    // Consider devices h -> g -> f -> e, not sorted by depth
    // f and e are virtual
    // e will be seen first and it won't have f as a parent available on the other host
    // so it won't be added
    // f will be added
    // then on second iteration e will find previously added f and will be added
    // So we're sorting to avoid the need to iterate devices N times where N is max depth of
    // virtual device nesting

    for virtual_device in virtual_devices {
        tracing::info!(
            "virtual_device: {:?}, parents: {:?}, children: {:?}",
            virtual_device.id,
            virtual_device.parents,
            virtual_device.children
        );
        let virtual_device_host =
            incoming_device_hosts.get(&(virtual_device.id.clone(), fqdn.clone()));

        tracing::info!(
            "virtual_device_host: {:?}, fqdn: {:?}",
            virtual_device_host.map(|x| &x.device_id),
            virtual_device_host.map(|x| &x.fqdn)
        );

        // For this host itself, run parents check for this virtual device ON THE INCOMING DEVICE HOSTS
        // If it fails, remove the device host of this virtual device FROM THE DB
        // We don't add virtual devices here because either:
        // 1. Device-scanner sends us the virtual device, if it's local on this host
        // 2. We will add it while processing other hosts, if it's not local on this host
        if virtual_device_host.is_some() {
            let local = virtual_device_host.map(|x| x.local).unwrap_or(false);
            let all_available = are_all_parents_available(
                incoming_devices,
                incoming_device_hosts,
                fqdn.clone(),
                &virtual_device.id,
            );
            tracing::trace!(
                "For this host: local: {:?}, all_available: {:?}",
                local,
                all_available
            );
            if !local {
                if !all_available {
                    // remove from db if present
                    let is_in_db = db_device_hosts
                        .get(&(virtual_device.id.clone(), fqdn.clone()))
                        .is_some();

                    if is_in_db {
                        remove_device_host(virtual_device.id.clone(), fqdn.clone(), &mut results);
                    }
                }
            } else {
                tracing::info!("Device host is local, skipping");
            }
        }

        // For all other hosts, run parents check for this virtual device ON THE DB
        // This is because main loop processes updates from single host at a time
        // That means current state of other hosts is in DB at this point
        let all_other_host_fqdns: BTreeSet<_> = db_device_hosts
            .iter()
            .chain(incoming_device_hosts.iter())
            .filter_map(|((_, f), _)| if true { Some(f) } else { None })
            .collect();
        tracing::trace!("all_other_host_fqdns: {:?}", all_other_host_fqdns);

        for host in all_other_host_fqdns {
            let all_available = are_all_parents_available_with_results(
                &all_devices,
                &all_device_hosts,
                &results,
                host.clone(),
                &virtual_device.id,
            );

            let db_device_host = db_device_hosts.get(&(virtual_device.id.clone(), host.clone()));
            let incoming_device_host =
                incoming_device_hosts.get(&(virtual_device.id.clone(), host.clone()));
            let is_in_db = db_device_host.is_some();
            let is_in_incoming = incoming_device_host.is_some() || virtual_device_host.is_some();

            let local = db_device_host
                .map(|x| x.local)
                .or_else(|| incoming_device_host.map(|x| x.local))
                .unwrap_or(false);
            tracing::debug!("DB device host: {:?}", db_device_host);
            tracing::debug!("Incoming device host: {:?}", incoming_device_host);
            // let new_device_host = db_device_host.or(incoming_device_host);

            if !local {
                if all_available {
                    // add to database if missing
                    // update in database if present

                    if !is_in_db {
                        add_device_host(
                            virtual_device.id.clone(),
                            host.clone(),
                            virtual_device_host,
                            &mut results,
                        );
                    } else if is_in_db {
                        if is_in_incoming {
                            update_device_host(
                                virtual_device.id.clone(),
                                host.clone(),
                                virtual_device_host,
                                &mut results,
                            );
                        }
                    } else {
                        let is_in_results = results
                            .get(&(virtual_device.id.clone(), host.clone()))
                            .is_none();

                        tracing::warn!(
                            "DB: {:?}, incoming: {:?}, results: {:?}",
                            is_in_db,
                            is_in_incoming,
                            is_in_results
                        );
                    }
                } else {
                    // remove from db if present
                    if is_in_db {
                        remove_device_host(virtual_device.id.clone(), host.clone(), &mut results);
                    }
                }
            } else {
                tracing::info!("Device host is local, skipping");
            }
        }
    }

    Ok(results)
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::db::test::{deser_devices, deser_fixture};
    use ::test_case::test_case;
    use insta::assert_debug_snapshot;

    #[test_case("vd_with_shared_parents_added_to_oss2")]
    #[test_case("vd_with_no_shared_parents_not_added_to_oss2")]
    // A leaf device has changed data on one host
    // It has to have updated data on the other one
    #[test_case("vd_with_shared_parents_updated_on_oss2")]
    // A leaf device is replaced with another leaf device
    // Previous one stays in the DB as available
    // We're not removing it since parents are still available
    #[test_case("vd_with_shared_parents_replaced_on_oss2")]
    #[test_case("vd_with_shared_parents_removed_from_oss2_when_parent_disappears")]
    #[test_case("vd_with_two_levels_of_shared_parents_added_to_oss2")]
    // An intermediary non-virtual parent disappears from the host
    // Its children are getting removed
    // Virtual devices from the other host receive updates that aren't necessary but aren't harmful
    #[test_case("vd_with_two_levels_of_shared_parents_removed_from_oss2_when_parent_disappears")]
    // A leaf virtual device is replaced with another virtual device on one host
    // Previous one stays in the DB as available
    // We're not removing it since parents are still available
    // Virtual device that is parent of the replaced receives update that isn't necessary but isn't harmful
    #[test_case("vd_with_two_levels_of_shared_parents_replaced_on_oss2")]
    // A leaf device has changed data on one host
    // It has to have updated data on the other one
    // Virtual device that is parent of the updated receives update that isn't necessary but isn't harmful
    #[test_case("vd_with_two_levels_of_shared_parents_updated_on_oss2")]
    #[test_case("vd_with_two_levels_of_shared_parents_in_reverse_order_added_to_oss2")]
    #[test_case("vd_with_three_levels_of_shared_parents_in_reverse_order_added_to_oss2")]
    // oss1 is processed completely on empty DB, with local VDs
    // oss2 is coming in second and it considers all other hosts for adding shared devices
    // that is oss1. oss2 is never considered to have added shared devices from oss1
    #[test_case("vd_with_shared_parents_added_after_oss1_to_oss2")]
    fn compute_virtual_device_changes(test_name: &str) {
        crate::db::test::_init_subscriber();
        let (fqdn, incoming_devices, incoming_device_hosts, db_devices, db_device_hosts) =
            deser_fixture(test_name);

        for ((_, f), dh) in incoming_device_hosts.iter() {
            assert_eq!(&fqdn, f);
            assert_eq!(fqdn, dh.fqdn);
        }

        let updates = super::compute_virtual_device_changes(
            &fqdn,
            &incoming_devices,
            &incoming_device_hosts,
            &db_devices,
            &db_device_hosts,
        )
        .unwrap();

        assert_debug_snapshot!(test_name, updates);
    }

    #[test_case("single_device_doesnt_iterate", "a")]
    #[test_case("single_parent_produces_one_item", "b")]
    #[test_case("two_parents_produce_two_items", "c")]
    #[test_case("parent_and_double_parent_produce_three_items", "c1")]
    #[test_case("triple_parent_and_double_parent_produce_five_items", "c1")]
    fn breadth_first_iterator(test_case: &str, child: &str) {
        let prefix = String::from("fixtures/") + test_case + "/";
        let devices = deser_devices(prefix.clone() + "devices.json");

        let id = DeviceId(child.into());
        let i = BreadthFirstParentIterator::new(&devices, &id);
        let result: Vec<_> = i.collect();
        assert_debug_snapshot!(test_case, result);
    }
}
