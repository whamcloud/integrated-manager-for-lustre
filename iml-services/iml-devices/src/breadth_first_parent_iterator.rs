// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::db::{Device, DeviceId};
use std::collections::{BTreeMap, BTreeSet};

/// Breadth-first iterator over parents of the device.
pub struct BreadthFirstParentIterator<'a, 'b> {
    devices: &'a BTreeMap<DeviceId, Device>,
    parents: BTreeSet<DeviceId>,
    next_parents: BTreeSet<DeviceId>,
    _marker: &'b std::marker::PhantomData<()>,
}

impl<'a, 'b> BreadthFirstParentIterator<'a, 'b> {
    /// Make a new iterator.
    /// 
    /// # Panics
    /// 
    /// If `device_id` is not found in `devices`.
    /// It means caller asked to start with device that's not present in the tree.
    pub fn new(devices: &'a BTreeMap<DeviceId, Device>, device_id: &'b DeviceId) -> Self {
        tracing::trace!("Getting {:?} from devices", device_id);
        let device = &devices[device_id];

        Self {
            devices,
            parents: device.parents.0.clone(),
            next_parents: BTreeSet::new(),
            _marker: &std::marker::PhantomData,
        }
    }
}

impl<'a, 'b> Iterator for BreadthFirstParentIterator<'a, 'b> {
    type Item = DeviceId;

    /// Iterate.
    /// 
    /// # Panics
    /// 
    /// If next parent device is not found in `devices`.
    /// It means tree is not consistent.
    fn next(&mut self) -> Option<DeviceId> {
        if self.parents.is_empty() {
            return None;
        }

        let p = self.parents.iter().next().unwrap().clone();
        tracing::trace!("Getting {:?} from devices", p);
        let parent_device = &self.devices[&p];
        let parent_parents = &parent_device.parents;

        for pp in parent_parents.iter() {
            self.next_parents.insert(pp.clone());
        }

        self.parents.remove(&p);

        if self.parents.is_empty() {
            self.parents = self.next_parents.clone();
            self.next_parents = BTreeSet::new();
        }

        Some(p)
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::db::test::deser_devices;
    use ::test_case::test_case;
    use insta::assert_debug_snapshot;

    #[test_case("single_device_doesnt_iterate", "a")]
    #[test_case("single_parent_produces_one_item", "b")]
    #[test_case("two_parents_produce_two_items", "c")]
    #[test_case("parent_and_double_parent_produce_three_items", "c1")]
    #[test_case("triple_parent_and_double_parent_produce_five_items", "c1")]
    #[test_case("three_parents_produce_three_items", "d")]
    fn breadth_first_iterator(test_case: &str, child: &str) {
        let prefix = String::from("fixtures/") + test_case + "/";
        let devices = deser_devices(prefix.clone() + "devices.json");

        let id = DeviceId(child.into());
        let i = BreadthFirstParentIterator::new(&devices, &id);
        let result: Vec<_> = i.collect();
        assert_debug_snapshot!(test_case, result);
    }
}
