// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod data;
pub mod db;
pub mod error;
pub mod local_actions;
pub mod receiver;
pub(crate) mod remote_action;
pub mod sender;

use emf_wire_types::{Fqdn, Id};
use futures::{channel::oneshot, lock::Mutex};
use std::{collections::HashMap, sync::Arc};

pub type Shared<T> = Arc<Mutex<T>>;
pub type Sessions = HashMap<Fqdn, Id>;
pub type Sender = oneshot::Sender<Result<serde_json::Value, String>>;
