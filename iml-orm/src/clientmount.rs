// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreLustreclientmount;
use crate::schema::chroma_core_lustreclientmount as client;
use diesel::{dsl, prelude::*};

pub type Table = client::table;
pub type NotDeleted = dsl::Eq<client::not_deleted, bool>;
pub type WithState = dsl::Eq<client::state, String>;
pub type WithoutIds = dsl::And<dsl::NeAny<client::id, Vec<i32>>, NotDeleted>;
pub type Available =
    dsl::Filter<client::table, dsl::And<dsl::And<WithoutIds, WithState>, NotDeleted>>;

impl ChromaCoreLustreclientmount {
    pub fn not_deleted() -> NotDeleted {
        client::not_deleted.eq(true)
    }
    pub fn with_state(state: impl ToString) -> WithState {
        client::state.eq(state.to_string())
    }
    pub fn without_ids(ids: impl IntoIterator<Item = i32>) -> WithoutIds {
        let xs: Vec<_> = ids.into_iter().collect();

        client::id.ne_all(xs).and(Self::not_deleted())
    }
    pub fn available(excluded_ids: impl IntoIterator<Item = i32>) -> Available {
        client::table.filter(
            Self::without_ids(excluded_ids)
                .and(Self::with_state("mounted"))
                .and(Self::not_deleted()),
        )
    }
}
