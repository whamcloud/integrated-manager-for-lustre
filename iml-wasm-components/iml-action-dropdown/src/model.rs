// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::hsm::HsmControlParam;
use std::collections::{HashMap, HashSet};

/// A record
#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct Record {
    pub content_type_id: i64,
    pub id: i64,
    pub label: String,
    pub hsm_control_params: Option<Vec<HsmControlParam>>,
    #[serde(flatten)]
    extra: Option<HashMap<String, serde_json::Value>>,
}

/// A record map is a map of composite id's to labels
pub type RecordMap = HashMap<String, Record>;

/// Records is a vector of Record items
pub type Records = Vec<Record>;

/// Data is what is being passed into the component.
#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct Data {
    pub records: Records,
    pub locks: Locks,
    pub flag: Option<String>,
    pub tooltip_placement: Option<iml_tooltip::TooltipPlacement>,
    pub tooltip_size: Option<iml_tooltip::TooltipSize>,
}

/// Metadata is the metadata object returned by a fetch call
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct MetaData {
    limit: u32,
    next: Option<u32>,
    offset: u32,
    previous: Option<u32>,
    total_count: u32,
}

/// AvailableActionsApiData contains the metadata and the `Vec` of objects returned by a fetch call
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct AvailableActionsApiData {
    pub meta: MetaData,
    pub objects: Vec<AvailableAction>,
}

/// ActionArgs contains the arguments to an action. It is currently not being used.
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq, Eq)]
pub struct ActionArgs {
    host_id: Option<u64>,
    target_id: Option<u64>,
}

/// AvailableAction represents an action that will be displayed on the dropdown.
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq, Eq)]
pub struct AvailableAction {
    pub args: Option<ActionArgs>,
    pub composite_id: String,
    pub class_name: Option<String>,
    pub confirmation: Option<String>,
    pub display_group: u64,
    pub display_order: u64,
    pub long_description: String,
    pub state: Option<String>,
    pub verb: String,
}

/// Combines the AvailableAction and Label
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct AvailableActionAndRecord {
    pub available_action: AvailableAction,
    pub record: Record,
    pub flag: Option<String>,
}

/// The ActionMap is a map consisting of actions grouped by the composite_id
pub type ActionMap = HashMap<String, Vec<AvailableAction>>;

/// Locks is a map of locks in which the key is a composite id string in the form `composite_id:id`
pub type Locks = HashMap<String, HashSet<LockChange>>;

/// The type of lock
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq, Hash, Clone)]
#[serde(rename_all = "lowercase")]
pub enum LockType {
    Read,
    Write,
}

/// The Action associated with a `LockChange`
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq, Hash, Clone)]
#[serde(rename_all = "lowercase")]
pub enum LockAction {
    Add,
    Remove,
}

/// A change to be applied to `Locks`
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq, Hash, Clone)]
pub struct LockChange {
    pub job_id: u64,
    pub content_type_id: u64,
    pub item_id: u64,
    pub description: String,
    pub lock_type: LockType,
    pub action: LockAction,
}

// Model
#[derive(Default)]
pub struct Model {
    pub records: RecordMap,
    pub available_actions: ActionMap,
    pub request_controller: Option<seed::fetch::RequestController>,
    pub cancel: Option<futures::sync::oneshot::Sender<()>>,
    pub locks: Locks,
    pub open: bool,
    pub button_activated: bool,
    pub first_fetch_active: bool,
    pub flag: Option<String>,
    pub tooltip: iml_tooltip::Model,
    pub destroyed: bool,
}
