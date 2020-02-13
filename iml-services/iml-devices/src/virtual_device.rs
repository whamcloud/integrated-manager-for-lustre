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

pub fn virtual_device_changes<'a>(
    fqdn: &Fqdn,
    incoming_devices: &Devices,
    incoming_device_hosts: &DeviceHosts,
    db_devices: &Devices,
    db_device_hosts: &DeviceHosts,
) -> Result<BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>, ImlDevicesError> {
    let results = BTreeMap::new();

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

        let changes = super::virtual_device_changes(
            &fqdn,
            &incoming_devices,
            &incoming_device_hosts,
            &db_devices,
            &db_device_hosts,
        )
        .unwrap();

        assert_debug_snapshot!(test_name, changes);
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
