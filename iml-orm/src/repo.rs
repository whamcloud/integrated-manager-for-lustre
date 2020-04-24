// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreRepo;
use crate::schema::chroma_core_repo as r;
use diesel::{dsl, prelude::*};

pub type Table = r::table;
pub type WithName = dsl::Eq<r::repo_name, String>;
pub type WithNames = dsl::EqAny<r::repo_name, Vec<String>>;
pub type ByName = dsl::Filter<Table, WithName>;
pub type ByNames = dsl::Filter<Table, WithNames>;

impl ChromaCoreRepo {
    pub fn all() -> Table {
        r::table
    }
    pub fn with_name(name: impl ToString) -> WithName {
        r::repo_name.eq(name.to_string())
    }
    pub fn with_names<S: ToString>(xs: impl IntoIterator<Item = S>) -> WithNames {
        let xs: Vec<_> = xs.into_iter().map(|x| x.to_string()).collect();

        r::repo_name.eq_any(xs)
    }
    pub fn by_name(name: impl ToString) -> ByName {
        Self::all().filter(Self::with_name(name))
    }
    pub fn by_names<S: ToString>(xs: impl IntoIterator<Item = S>) -> ByNames {
        Self::all().filter(Self::with_names(xs))
    }
}
