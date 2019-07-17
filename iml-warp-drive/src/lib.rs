// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod cache;
pub mod db_record;
pub mod listen;
pub mod locks;
pub mod request;
pub mod users;

pub use db_record::*;

/// Message variants.
#[derive(serde::Serialize, Clone, Debug)]
#[serde(tag = "tag", content = "payload")]
pub enum Message {
    Locks(locks::Locks),
    Records(cache::Cache),
    RecordChange(cache::RecordChange),
}
