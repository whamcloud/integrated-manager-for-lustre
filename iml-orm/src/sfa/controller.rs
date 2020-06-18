// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::HealthState;
#[cfg(feature = "postgres-interop")]
use crate::{schema::chroma_core_sfacontroller as sc, Executable, Upserts};
#[cfg(feature = "postgres-interop")]
use diesel::{
    dsl,
    pg::{upsert::excluded, Pg},
    prelude::*,
    Queryable,
};

#[cfg(feature = "postgres-interop")]
pub type Table = sc::table;
#[cfg(feature = "postgres-interop")]
pub type WithIndexes = dsl::EqAny<sc::index, Vec<i32>>;
#[cfg(feature = "postgres-interop")]
pub type WithStorageSystem<'a> = dsl::EqAny<sc::storage_system, Vec<&'a str>>;
#[cfg(feature = "postgres-interop")]
pub type ByRecords<'a> = dsl::Filter<Table, dsl::And<WithIndexes, WithStorageSystem<'a>>>;

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(Insertable, AsChangeset))]
#[cfg_attr(feature = "postgres-interop", table_name = "sc")]
pub struct SfaController {
    pub index: i32,
    pub enclosure_index: i32,
    pub health_state: HealthState,
    pub health_state_reason: String,
    pub child_health_state: HealthState,
    pub storage_system: String,
}

impl crate::Identifiable for SfaController {
    type Id = String;

    fn id(&self) -> Self::Id {
        format!("{}_{}", self.index, self.storage_system)
    }
}

#[cfg(feature = "postgres-interop")]
impl Queryable<sc::SqlType, Pg> for SfaController {
    type Row = (i32, i32, i32, HealthState, String, HealthState, String);

    fn build(row: Self::Row) -> Self {
        Self {
            index: row.1,
            enclosure_index: row.2,
            health_state: row.3,
            health_state_reason: row.4,
            child_health_state: row.5,
            storage_system: row.6,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl SfaController {
    pub fn all() -> sc::table {
        sc::table
    }

    pub fn batch_upsert(x: Upserts<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all())
            .values(x.0)
            .on_conflict((sc::index, sc::storage_system))
            .do_update()
            .set((
                sc::enclosure_index.eq(excluded(sc::enclosure_index)),
                sc::health_state.eq(excluded(sc::health_state)),
                sc::health_state_reason.eq(excluded(sc::health_state_reason)),
                sc::child_health_state.eq(excluded(sc::child_health_state)),
            ))
    }
    fn batch_delete_filter<'a>(xs: Vec<&'a Self>) -> ByRecords<'a> {
        let (indexes, storage_systems): (Vec<_>, Vec<_>) = xs
            .into_iter()
            .map(|x| (x.index, x.storage_system.as_str()))
            .unzip();

        Self::all().filter(
            sc::index
                .eq_any(indexes)
                .and(sc::storage_system.eq_any(storage_systems)),
        )
    }
    pub fn batch_delete<'a>(xs: Vec<&'a Self>) -> impl Executable + 'a {
        diesel::delete(Self::batch_delete_filter(xs))
    }
}
