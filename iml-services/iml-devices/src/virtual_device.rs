// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    build_new_state::{build_new_state, is_virtual_device},
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

fn diff(old: &DeviceHosts, new: &DeviceHosts) -> BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>> {
    let mut results = BTreeMap::new();

    let union = {
        let mut new = new.clone();
        let mut old = old.clone();
        let mut union = BTreeMap::new();
        union.append(&mut old);
        union.append(&mut new);
        union
    };

    for ((id, f), _dh) in union.into_iter() {
        let old = old.get(&(id.clone(), f.clone()));
        let new = new.get(&(id.clone(), f.clone()));

        tracing::trace!(
            "{} {}",
            old.map(|o| format!("{}", o)).unwrap_or("None".into()),
            new.map(|o| format!("{}", o)).unwrap_or("None".into()),
        );

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

    results
}

fn non_local_virtual_device_hosts(device_hosts: DeviceHosts, devices: &Devices) -> DeviceHosts {
    device_hosts
        .into_iter()
        .filter(|((id, _), dh)| {
            devices
                .get(id)
                .map(|d| is_virtual_device(d))
                .unwrap_or(false)
                && !dh.local
        })
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect()
}

pub fn virtual_device_changes<'a>(
    fqdn: &Fqdn,
    incoming_devices: &Devices,
    incoming_device_hosts: &DeviceHosts,
    db_devices: &Devices,
    db_device_hosts: &DeviceHosts,
) -> Result<BTreeMap<(DeviceId, Fqdn), Change<DeviceHost>>, ImlDevicesError> {
    let (new_devices, new_device_hosts) = build_new_state(
        fqdn,
        incoming_devices,
        incoming_device_hosts,
        db_devices,
        db_device_hosts,
    );

    let db_device_hosts = non_local_virtual_device_hosts(db_device_hosts.clone(), db_devices);
    let new_device_hosts = non_local_virtual_device_hosts(new_device_hosts, &new_devices);

    let results = diff(&db_device_hosts, &new_device_hosts);

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
    #[test_case("vd_with_shared_parents_replaced_on_oss2")]
    #[test_case("vd_with_shared_parents_removed_from_oss2_when_parent_disappears")]
    #[test_case("vd_with_two_levels_of_shared_parents_added_to_oss2")]
    // An intermediary non-virtual parent disappears from the host
    // Its children are getting removed
    #[test_case("vd_with_two_levels_of_shared_parents_removed_from_oss2_when_parent_disappears")]
    // A leaf virtual device is replaced with another virtual device on one host
    #[test_case("vd_with_two_levels_of_shared_parents_replaced_on_oss2")]
    // A leaf device has changed data on one host
    // It has to have updated data on the other one
    #[test_case("vd_with_two_levels_of_shared_parents_updated_on_oss2")]
    #[test_case("vd_with_two_levels_of_shared_parents_in_reverse_order_added_to_oss2")]
    #[test_case("vd_with_three_levels_of_shared_parents_in_reverse_order_added_to_oss2")]
    // oss1 is processed completely on empty DB, with local VDs
    // oss2 is coming in second and it considers all other hosts for adding shared devices
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

    #[test_case("vd_with_shared_parents_added_to_oss2")]
    #[test_case("vd_with_no_shared_parents_not_added_to_oss2")]
    #[test_case("vd_with_shared_parents_updated_on_oss2")]
    #[test_case("vd_with_shared_parents_replaced_on_oss2")]
    #[test_case("vd_with_shared_parents_removed_from_oss2_when_parent_disappears")]
    #[test_case("vd_with_two_levels_of_shared_parents_added_to_oss2")]
    #[test_case("vd_with_two_levels_of_shared_parents_removed_from_oss2_when_parent_disappears")]
    #[test_case("vd_with_two_levels_of_shared_parents_replaced_on_oss2")]
    #[test_case("vd_with_two_levels_of_shared_parents_updated_on_oss2")]
    #[test_case("vd_with_two_levels_of_shared_parents_in_reverse_order_added_to_oss2")]
    #[test_case("vd_with_three_levels_of_shared_parents_in_reverse_order_added_to_oss2")]
    #[test_case("vd_with_shared_parents_added_after_oss1_to_oss2")]
    fn diff(test_name: &str) {
        crate::db::test::_init_subscriber();
        let (fqdn, incoming_devices, incoming_device_hosts, db_devices, db_device_hosts) =
            deser_fixture(test_name);

        for ((_, f), dh) in incoming_device_hosts.iter() {
            assert_eq!(&fqdn, f);
            assert_eq!(fqdn, dh.fqdn);
        }

        let (new_devices, new_device_hosts) = build_new_state(
            &fqdn,
            &incoming_devices,
            &incoming_device_hosts,
            &db_devices,
            &db_device_hosts,
        );

        let db_device_hosts = non_local_virtual_device_hosts(db_device_hosts, &db_devices);
        let new_device_hosts = non_local_virtual_device_hosts(new_device_hosts, &new_devices);
    
        let results = super::diff(&db_device_hosts, &new_device_hosts);

        assert_debug_snapshot!(test_name, results);
    }
}
