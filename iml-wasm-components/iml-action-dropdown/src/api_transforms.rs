// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{ActionMap, AvailableAction, LockChange, LockType, Locks, RecordMap};
use std::collections::HashMap;

pub fn record_to_composite_id_string(c: i64, i: i64) -> String {
    format!("{}:{}", c, i)
}

pub fn lock_list<'a>(
    locks: &'a Locks,
    records: &'a RecordMap,
) -> impl Iterator<Item = &'a LockChange> {
    records
        .keys()
        .filter_map(move |x| locks.get(x))
        .flatten()
        .filter(|x| x.lock_type == LockType::Write)
}

pub fn composite_ids_to_query_string(x: &RecordMap) -> String {
    let mut xs: Vec<String> = x
        .keys()
        .map(|x| format!("composite_ids={}", x))
        .collect::<Vec<String>>();

    xs.sort();
    xs.join("&")
}

pub fn group_actions_by_label(objects: Vec<AvailableAction>, records: &RecordMap) -> ActionMap {
    objects
        .into_iter()
        .fold(HashMap::new(), |mut obj: ActionMap, action| {
            let record = &records[&action.composite_id];

            match obj.get_mut(&record.label) {
                Some(xs) => xs.push(action),
                None => {
                    obj.insert(record.label.to_string(), vec![action]);
                }
            };

            obj
        })
}

/// Sort items by display_group, then by display_order. Mark the last item in each group
pub fn sort_actions(mut actions: Vec<AvailableAction>) -> Vec<AvailableAction> {
    actions.sort_by(|a, b| a.display_group.cmp(&b.display_group));
    actions.sort_by(|a, b| a.display_order.cmp(&b.display_order));
    actions
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ActionArgs, LockAction, Record};
    use insta::assert_debug_snapshot_matches;
    use std::collections::HashMap;

    #[test]
    fn test_lock_list() {
        let lock1 = LockChange {
            job_id: 53,
            content_type_id: 61,
            item_id: 1,
            description:
                "Shut down the LNet networking layer and stop any targets running on this server."
                    .into(),
            lock_type: LockType::Write,
            action: LockAction::Add,
        };

        let lock2 = LockChange {
            job_id: 54,
            content_type_id: 49,
            item_id: 2,
            description: "Stop Pacemaker on mds2.local".into(),
            lock_type: LockType::Write,
            action: LockAction::Add,
        };

        let mut locks = HashMap::new();

        locks.insert("61:1".to_string(), [lock1].iter().cloned().collect());
        locks.insert("49:2".to_string(), [lock2].iter().cloned().collect());

        let mut records = HashMap::new();
        records.insert(
            "61:1".to_string(),
            Record {
                content_type_id: 61,
                id: 1,
                label: "label1".to_string(),
                hsm_control_params: None,
                extra: None,
            },
        );

        let xs: Vec<&LockChange> = lock_list(&locks, &records).collect();

        assert_debug_snapshot_matches!("locks_list", xs);
    }

    #[test]
    fn test_composite_ids_to_query_string() {
        let mut records = HashMap::new();
        records.insert(
            "57:3".to_string(),
            Record {
                content_type_id: 57,
                id: 3,
                label: "Label2".to_string(),
                hsm_control_params: None,
                extra: None,
            },
        );
        records.insert(
            "49:1".to_string(),
            Record {
                content_type_id: 49,
                id: 1,
                label: "Label1".to_string(),
                hsm_control_params: None,
                extra: None,
            },
        );

        let query_string = composite_ids_to_query_string(&records);

        assert_eq!(query_string, "composite_ids=49:1&composite_ids=57:3");
    }

    #[test]
    fn test_record_to_composite_id_string() {
        assert_eq!(record_to_composite_id_string(61, 2), "61:2".to_string());
    }

    #[test]
    fn test_group_actions_by_label() {
        let action_item1 = AvailableAction {
            args: Some(ActionArgs {
                host_id: Some(1),
                target_id: None
            }),
            class_name: Some("RebootHostJob".to_string()),
            composite_id: "62:1".to_string(),
            confirmation: None,
            display_group: 2,
            display_order: 50,
            long_description: "Initiate a reboot on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has finished rebooting.".to_string(),
            state: None,
            verb: "Reboot".to_string()
        };

        let action_item2 = AvailableAction {
            args: Some(ActionArgs {
                host_id: Some(1),
                target_id: None
            }),
            class_name: Some("ShutdownHostJob".to_string()),
            composite_id: "62:1".to_string(),
            confirmation: Some("Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string()),
            display_group: 2,
            display_order: 60,
            long_description: "Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string(),
            state: None,
            verb: "Shutdown".to_string()
        };

        let action_item3 = AvailableAction {
            args: Some(ActionArgs {
                host_id: Some(2),
                target_id: None
            }),
            class_name: Some("RebootHostJob".to_string()),
            composite_id: "62:2".to_string(),
            confirmation: None,
            display_group: 2,
            display_order: 50,
            long_description: "Initiate a reboot on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has finished rebooting.".to_string(),
            state: None,
            verb: "Reboot".to_string()
        };

        let action_item4 = AvailableAction {
            args: Some( ActionArgs {
                host_id: Some(2),
                target_id: None
            }),
            class_name: Some("ShutdownHostJob".to_string()),
            composite_id: "62:2".to_string(),
            confirmation: Some("Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string()),
            display_group: 2,
            display_order: 60,
            long_description: "Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string(),
            state: None,
            verb: "Shutdown".to_string()
        };

        let objects = vec![action_item1, action_item4, action_item3, action_item2];

        let mut records: RecordMap = HashMap::new();
        records.insert(
            "62:1".to_string(),
            Record {
                content_type_id: 62,
                id: 1,
                label: "Label1".to_string(),
                hsm_control_params: None,
                extra: None,
            },
        );
        records.insert(
            "62:2".to_string(),
            Record {
                content_type_id: 62,
                id: 2,
                label: "Label2".to_string(),
                hsm_control_params: None,
                extra: None,
            },
        );

        let groups: ActionMap = group_actions_by_label(objects, records)
            .into_iter()
            .map(|(k, xs)| (k, sort_actions(xs)))
            .collect();

        assert_debug_snapshot_matches!(
            "group_actions_by_label_1",
            groups.get(&"Label1".to_string())
        );

        assert_debug_snapshot_matches!(
            "group_actions_by_label_2",
            groups.get(&"Label2".to_string())
        );
    }

    #[test]
    fn test_sort_actions() {
        let action_item1 = AvailableAction {
            args: Some(ActionArgs {
                host_id: Some(1),
                target_id: None
            }),
            class_name: Some("RebootHostJob".to_string()),
            composite_id: "62:1".to_string(),
            confirmation: None,
            display_group: 2,
            display_order: 50,
            long_description: "Initiate a reboot on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has finished rebooting.".to_string(),
            state: None,
            verb: "Reboot".to_string()
        };

        let action_item2 = AvailableAction {
            args: Some(ActionArgs {
                host_id: Some(1),
                target_id: None
            }),
            class_name: Some("ShutdownHostJob".to_string()),
            composite_id: "62:1".to_string(),
            confirmation: Some("Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string()),
            display_group: 2,
            display_order: 60,
            long_description: "Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string(),
            state: None,
            verb: "Shutdown".to_string()
        };

        let action_item3 = AvailableAction {
            args: Some(ActionArgs {
                host_id: Some(1),
                target_id: None
            }),
            class_name: Some("RebootHostJob".to_string()),
            composite_id: "62:1".to_string(),
            confirmation: None,
            display_group: 4,
            display_order: 120,
            long_description: "Initiate a reboot on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has finished rebooting.".to_string(),
            state: None,
            verb: "Reboot".to_string()
        };

        let action_item4 = AvailableAction {
            args: Some( ActionArgs {
                host_id: Some(1),
                target_id: None
            }),
            class_name: Some("ShutdownHostJob".to_string()),
            composite_id: "62:1".to_string(),
            confirmation: Some("Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string()),
            display_group: 4,
            display_order: 150,
            long_description: "Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.".to_string(),
            state: None,
            verb: "Shutdown".to_string()
        };

        let action_item1_clone = action_item1.clone();
        let action_item2_clone = action_item2.clone();
        let action_item3_clone = action_item3.clone();
        let action_item4_clone = action_item4.clone();

        let actions = vec![action_item4, action_item1, action_item3, action_item2];
        let sorted_actions = sort_actions(actions);

        assert_eq!(
            sorted_actions,
            vec![
                action_item1_clone,
                action_item2_clone,
                action_item3_clone,
                action_item4_clone
            ]
        )
    }
}
