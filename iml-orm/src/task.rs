// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreTask;
use crate::schema::chroma_core_task as task;
use diesel::{dsl, prelude::*};

pub type Table = task::table;
pub type WithName = dsl::Eq<task::name, String>;
pub type ByName = dsl::Filter<task::table, WithName>;

impl ChromaCoreTask {
    pub fn all() -> Table {
        task::table
    }
    pub fn with_name(name: impl ToString) -> WithName {
        task::name.eq(name.to_string())
    }
    pub fn by_name(name: impl ToString) -> ByName {
        task::table.filter(Self::with_name(name))
    }
}
