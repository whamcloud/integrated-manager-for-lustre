// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_utils::Locks;
use iml_wire_types::{
    ApiList, AvailableAction, CompositeId, HsmControlParam, Label, LockChange, LockType,
    ToCompositeId,
};
use std::{collections::HashMap, convert, iter};

/// A record
#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct Record {
    pub content_type_id: u32,
    pub id: u32,
    pub label: String,
    pub hsm_control_params: Option<Vec<HsmControlParam>>,
    #[serde(flatten)]
    extra: Option<HashMap<String, serde_json::Value>>,
}

impl ToCompositeId for Record {
    fn composite_id(&self) -> CompositeId {
        CompositeId(self.content_type_id, self.id)
    }
}

impl Label for Record {
    fn label(&self) -> &str {
        &self.label
    }
}

pub trait ActionRecord: ToCompositeId + serde::Serialize + Label + Clone {}
impl<T: ToCompositeId + serde::Serialize + Label + Clone> ActionRecord for T {}

/// A map of composite id's to labels
pub type RecordMap<T> = HashMap<String, T>;

pub type AvailableActions = ApiList<AvailableAction>;

/// Combines the AvailableAction and Label
#[derive(serde::Serialize, Clone, Debug)]
pub struct AvailableActionAndRecord<T: ActionRecord> {
    pub available_action: AvailableAction,
    pub record: T,
    pub flag: Option<String>,
}

/// The ActionMap is a map consisting of actions grouped by the composite_id
pub type ActionMap<'a, T> = HashMap<String, Vec<(&'a AvailableAction, &'a T)>>;

fn lock_list<'a, T>(
    locks: &'a Locks,
    records: &'a RecordMap<T>,
) -> impl Iterator<Item = &'a LockChange> {
    records
        .keys()
        .filter_map(move |x| locks.get(x))
        .flatten()
        .filter(|x| x.lock_type == LockType::Write)
}

pub fn has_lock<'a, T: ActionRecord>(locks: &'a Locks, record: &'a T) -> bool {
    let id = record.composite_id().to_string();

    iter::once(locks.get(&id))
        .filter_map(convert::identity)
        .flatten()
        .any(|x| x.lock_type == LockType::Write)
}

pub fn has_locks<'a, T>(locks: &'a Locks, records: &'a RecordMap<T>) -> bool {
    lock_list(&locks, &records).next().is_some()
}

pub fn composite_ids_to_query_string(xs: &[CompositeId]) -> String {
    let mut xs: Vec<String> = xs
        .iter()
        .map(|x| format!("composite_ids={}", x))
        .collect::<Vec<String>>();

    xs.sort();
    xs.join("&")
}

pub fn group_actions_by_label<'a, T: ActionRecord>(
    objects: &'a [AvailableAction],
    records: &'a RecordMap<T>,
) -> ActionMap<'a, T> {
    objects.iter().fold(HashMap::new(), |mut obj, action| {
        let record = &records[&action.composite_id];

        match obj.get_mut(record.label()) {
            Some(xs) => xs.push((action, record)),
            None => {
                obj.insert(record.label().to_string(), vec![(action, record)]);
            }
        };

        obj
    })
}

/// Sort items by display_group, then by display_order.
pub fn sort_actions<'a, T>(
    mut actions: Vec<(&'a AvailableAction, &'a T)>,
) -> Vec<(&'a AvailableAction, &'a T)> {
    actions.sort_by(|a, b| a.0.display_group.cmp(&b.0.display_group));
    actions.sort_by(|a, b| a.0.display_order.cmp(&b.0.display_order));
    actions
}

pub fn record_to_map<T: ActionRecord>(x: T) -> (String, T) {
    (x.composite_id().to_string(), x)
}

pub fn records_to_map<T: ActionRecord>(xs: Vec<T>) -> RecordMap<T> {
    xs.into_iter().map(record_to_map).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Record;
    use iml_wire_types::{ActionArgs, LockAction};
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
        let query_string = composite_ids_to_query_string(&[CompositeId(57, 3), CompositeId(49, 1)]);

        assert_eq!(query_string, "composite_ids=49:1&composite_ids=57:3");
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

        let objects = &[action_item1, action_item4, action_item3, action_item2];

        let mut records: RecordMap<Record> = HashMap::new();
        records.insert(
            "62:1".into(),
            Record {
                content_type_id: 62,
                id: 1,
                label: "Label1".into(),
                hsm_control_params: None,
                extra: None,
            },
        );
        records.insert(
            "62:2".into(),
            Record {
                content_type_id: 62,
                id: 2,
                label: "Label2".into(),
                hsm_control_params: None,
                extra: None,
            },
        );

        let groups: ActionMap<Record> = group_actions_by_label(objects, &records)
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

        let record = Record {
            content_type_id: 62,
            id: 2,
            label: "Label2".into(),
            hsm_control_params: None,
            extra: None,
        };

        let actions = vec![
            (&action_item4, &record),
            (&action_item1, &record),
            (&action_item3, &record),
            (&action_item2, &record),
        ];
        let sorted_actions = sort_actions(actions);

        assert_eq!(
            sorted_actions,
            vec![
                (&action_item1_clone, &record),
                (&action_item2_clone, &record),
                (&action_item3_clone, &record),
                (&action_item4_clone, &record),
            ]
        )
    }
}
