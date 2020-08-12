// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreManagedfilesystem;

use crate::schema::chroma_core_managedfilesystem as fs;
use diesel::{dsl, prelude::*};

pub type Table = fs::table;
pub type NotDeleted = dsl::Eq<fs::not_deleted, bool>;
pub type WithState = dsl::Eq<fs::state, String>;
pub type WithName = dsl::And<dsl::Eq<fs::name, String>, NotDeleted>;
pub type AllAvailable = dsl::Filter<Table, WithState>;
pub type ByName = dsl::Filter<Table, WithName>;

impl ChromaCoreManagedfilesystem {
    pub fn all() -> Table {
        fs::table
    }
    pub fn not_deleted() -> NotDeleted {
        fs::not_deleted.eq(true)
    }
    pub fn with_name(name: impl ToString) -> WithName {
        fs::name.eq(name.to_string()).and(Self::not_deleted())
    }
    pub fn with_state(name: impl ToString) -> WithState {
        fs::state.eq(name.to_string())
    }
    pub fn by_name(name: impl ToString) -> ByName {
        Self::all().filter(Self::with_name(name))
    }
    pub fn all_available() -> AllAvailable {
        Self::all().filter(Self::with_state("available"))
    }
}
