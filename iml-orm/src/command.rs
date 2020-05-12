// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreCommand;
use crate::schema::chroma_core_command as command;
use diesel::{dsl, prelude::*};

pub type Table = command::table;
pub type WithId = dsl::Eq<command::id, i32>;
pub type ById = dsl::Filter<command::table, WithId>;

impl ChromaCoreCommand {
    pub fn all() -> Table {
        command::table
    }
    pub fn with_id(id: i32) -> WithId {
        command::id.eq(id)
    }
    pub fn by_id(id: i32) -> ById {
        command::table.filter(Self::with_id(id))
    }
}
