// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::db::{DeviceHosts, Devices};
use iml_wire_types::Fqdn;
use std::collections::BTreeSet;

pub fn merge_state(
    fqdn: &Fqdn,
    incoming_devices: &Devices,
    incoming_device_hosts: &DeviceHosts,
    db_devices: &Devices,
    db_device_hosts: &DeviceHosts,
) -> (Devices, DeviceHosts) {
    assert!(incoming_device_hosts
        .iter()
        .all(|((_, f), dh)| f == fqdn && &dh.fqdn == fqdn));

    let device_hosts: DeviceHosts = db_device_hosts
        .iter()
        .filter(|((_, f), _)| f != fqdn)
        .chain(incoming_device_hosts)
        .map(|(x, y)| (x.clone(), y.clone()))
        .collect();

    let device_ids: BTreeSet<_> = device_hosts
        .iter()
        .filter_map(|((id, _), dh)| if dh.local { Some(id) } else { None })
        .collect();

    let devices = db_devices
        .iter()
        .chain(incoming_devices)
        .filter(|(id, _)| device_ids.get(id).is_some())
        .map(|(x, y)| (x.clone(), y.clone()))
        .collect();

    (devices, device_hosts)
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::db::test::deser_fixture;
    use insta::assert_debug_snapshot;
    use test_case::test_case;

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
    fn merge_state(test_name: &str) {
        crate::db::test::_init_subscriber();
        let (fqdn, incoming_devices, incoming_device_hosts, db_devices, db_device_hosts) =
            deser_fixture(test_name);

        for ((_, f), dh) in incoming_device_hosts.iter() {
            assert_eq!(&fqdn, f);
            assert_eq!(fqdn, dh.fqdn);
        }

        let state = super::merge_state(
            &fqdn,
            &incoming_devices,
            &incoming_device_hosts,
            &db_devices,
            &db_device_hosts,
        );

        assert_debug_snapshot!(test_name, state);
    }
}
