// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    build_new_state::build_new_state,
    change::Change,
    db::{DeviceHosts, Devices},
    error::ImlDevicesError,
};
use iml_wire_types::{
    db::{DeviceHost, DeviceId, MountPath, Paths},
    Fqdn,
};
use std::collections::{BTreeMap, BTreeSet};

pub fn make_other_device_host(
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

pub fn virtual_device_changes<'a>(
    fqdn: &Fqdn,
    incoming_devices: &Devices,
    incoming_device_hosts: &DeviceHosts,
    db_devices: &Devices,
    db_device_hosts: &DeviceHosts,
) -> Result<BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>, ImlDevicesError> {
    let mut results = BTreeMap::new();

    let (_new_devices, new_device_hosts) = build_new_state(
        fqdn,
        incoming_devices,
        incoming_device_hosts,
        db_devices,
        db_device_hosts,
    );
    let old_device_hosts = db_device_hosts;

    let union = {
        let mut new_device_hosts = new_device_hosts.clone();
        let mut db_device_hosts = db_device_hosts.clone();
        let mut union = BTreeMap::new();
        union.append(&mut db_device_hosts);
        union.append(&mut new_device_hosts);
        union
    };

    for ((id, f), _dh) in union.into_iter() {
        let old = old_device_hosts.get(&(id.clone(), f.clone()));
        let new = new_device_hosts.get(&(id.clone(), f.clone()));
        let change = match (old, new) {
            (None, None) => unreachable!(),
            (None, Some(dh)) => Some(Change::Add(dh.clone())),
            (Some(dh), None) => Some(Change::Remove(dh.clone())),
            (Some(old), Some(new)) => {
                if old != new {
                    Some(Change::Update(new.clone()))
                } else {
                    None
                }
            }
        };
        change.map(|c| results.insert((id, f), c));
    }

    Ok(results)
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::db::test::deser_fixture;
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
    fn virtual_device_changes(test_name: &str) {
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
}
