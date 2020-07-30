// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreManagedhost;
use crate::schema::chroma_core_managedhost as mh;
use diesel::{dsl, prelude::*};

pub type Table = mh::table;
pub type NotDeleted = dsl::Eq<mh::not_deleted, bool>;
pub type WithFqdn = dsl::And<dsl::Eq<mh::fqdn, String>, NotDeleted>;
pub type WithId = dsl::And<dsl::Eq<mh::id, i32>, NotDeleted>;
pub type ByFqdn = dsl::Filter<Table, WithFqdn>;
pub type ById = dsl::Filter<Table, WithId>;

impl ChromaCoreManagedhost {
    pub fn all() -> Table {
        mh::table
    }
    pub fn not_deleted() -> NotDeleted {
        mh::not_deleted.eq(true)
    }
    pub fn with_fqdn(name: impl ToString) -> WithFqdn {
        mh::fqdn.eq(name.to_string()).and(Self::not_deleted())
    }
    pub fn with_id(id: i32) -> WithId {
        mh::id.eq(id).and(Self::not_deleted())
    }
    pub fn by_fqdn(fqdn: impl ToString) -> ByFqdn {
        Self::all().filter(Self::with_fqdn(fqdn))
    }
    pub fn by_id(id: i32) -> ById {
        Self::all().filter(Self::with_id(id))
    }
    pub fn is_setup(&self) -> bool {
        ["monitored", "managed", "working"]
            .iter()
            .any(|&x| x == self.state)
    }
}