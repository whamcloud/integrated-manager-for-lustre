// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod data;
pub mod error;
pub mod local_actions;
pub mod receiver;
pub mod sender;

use futures::{channel::oneshot, lock::Mutex};
use iml_wire_types::{Action, Fqdn, Id};
use std::{collections::HashMap, sync::Arc};

pub type Shared<T> = Arc<Mutex<T>>;
pub type Sessions = HashMap<Fqdn, Id>;
pub type Sender = oneshot::Sender<Result<serde_json::Value, String>>;

/// Actions can be run either locally or remotely.
/// Besides the node these are run on, the interface should
/// be the same.
///
/// This should probably be collapsed into a single struct over an enum at some point.
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ActionType {
    Remote((Fqdn, Action)),
    Local(Action),
}
