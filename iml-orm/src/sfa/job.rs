// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::{JobState, JobType, SubTargetType};
#[cfg(feature = "postgres-interop")]
use crate::{schema::chroma_core_sfajob as sj, Executable, Upserts};
#[cfg(feature = "postgres-interop")]
use diesel::{
    self, dsl,
    pg::{upsert::excluded, Pg},
    prelude::*,
    Queryable,
};

#[cfg(feature = "postgres-interop")]
pub type Table = sj::table;
#[cfg(feature = "postgres-interop")]
pub type WithIndexes = dsl::EqAny<sj::index, Vec<i32>>;
#[cfg(feature = "postgres-interop")]
pub type WithStorageSystem<'a> = dsl::EqAny<sj::storage_system, Vec<&'a str>>;
#[cfg(feature = "postgres-interop")]
pub type ByRecords<'a> = dsl::Filter<Table, dsl::And<WithIndexes, WithStorageSystem<'a>>>;

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(Insertable, AsChangeset))]
#[cfg_attr(feature = "postgres-interop", table_name = "sj")]
pub struct SfaJob {
    pub index: i32,
    pub sub_target_index: Option<i32>,
    pub sub_target_type: Option<SubTargetType>,
    pub job_type: JobType,
    pub state: JobState,
    pub storage_system: String,
}

impl crate::Identifiable for SfaJob {
    type Id = String;

    fn id(&self) -> Self::Id {
        format!("{}_{}", self.index, self.storage_system)
    }
}

#[cfg(feature = "postgres-interop")]
impl SfaJob {
    pub fn all() -> sj::table {
        sj::table
    }
    pub fn batch_upsert(x: Upserts<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all())
            .values(x.0)
            .on_conflict((sj::index, sj::storage_system))
            .do_update()
            .set((
                sj::sub_target_index.eq(excluded(sj::sub_target_index)),
                sj::sub_target_type.eq(excluded(sj::sub_target_type)),
                sj::job_type.eq(excluded(sj::job_type)),
                sj::state.eq(excluded(sj::state)),
            ))
    }
    fn batch_delete_filter<'a>(xs: Vec<&'a Self>) -> ByRecords<'a> {
        let (indexes, storage_systems): (Vec<_>, Vec<_>) = xs
            .into_iter()
            .map(|x| (x.index, x.storage_system.as_str()))
            .unzip();

        Self::all().filter(
            sj::index
                .eq_any(indexes)
                .and(sj::storage_system.eq_any(storage_systems)),
        )
    }
    pub fn batch_delete<'a>(xs: Vec<&'a Self>) -> impl Executable + 'a {
        diesel::delete(Self::batch_delete_filter(xs))
    }
}

#[cfg(feature = "postgres-interop")]
impl Queryable<sj::SqlType, Pg> for SfaJob {
    type Row = (
        i32,
        i32,
        Option<i32>,
        Option<SubTargetType>,
        JobType,
        JobState,
        String,
    );

    fn build(row: Self::Row) -> Self {
        Self {
            index: row.1,
            sub_target_index: row.2,
            sub_target_type: row.3,
            job_type: row.4,
            state: row.5,
            storage_system: row.6,
        }
    }
}
