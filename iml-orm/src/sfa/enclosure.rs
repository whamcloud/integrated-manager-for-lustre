// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::{EnclosureType, HealthState};
#[cfg(feature = "postgres-interop")]
use crate::{schema::chroma_core_sfaenclosure as se, Executable, Upserts};
#[cfg(feature = "postgres-interop")]
use diesel::{
    self, dsl,
    pg::{upsert::excluded, Pg},
    prelude::*,
    Queryable,
};

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(Insertable, AsChangeset))]
#[cfg_attr(feature = "postgres-interop", table_name = "se")]
pub struct SfaEnclosure {
    /// Specifies the index, part of the OID, of the enclosure.
    pub index: i32,
    pub element_name: String,
    pub health_state: HealthState,
    pub health_state_reason: String,
    pub child_health_state: HealthState,
    pub model: String,
    pub position: i16,
    pub enclosure_type: EnclosureType,
    pub canister_location: String,
    pub storage_system: String,
}

impl crate::Identifiable for SfaEnclosure {
    type Id = String;

    fn id(&self) -> Self::Id {
        format!("{}_{}", self.index, self.storage_system)
    }
}

#[cfg(feature = "postgres-interop")]
impl Queryable<se::SqlType, Pg> for SfaEnclosure {
    type Row = (
        i32,
        i32,
        String,
        HealthState,
        String,
        HealthState,
        String,
        i16,
        EnclosureType,
        String,
        String,
    );

    fn build(row: Self::Row) -> Self {
        Self {
            index: row.1,
            element_name: row.2,
            health_state: row.3,
            health_state_reason: row.4,
            child_health_state: row.5,
            model: row.6,
            position: row.7,
            enclosure_type: row.8,
            canister_location: row.9,
            storage_system: row.10,
        }
    }
}

#[cfg(feature = "postgres-interop")]
pub type Table = se::table;
#[cfg(feature = "postgres-interop")]
pub type WithIndexes = dsl::EqAny<se::index, Vec<i32>>;
#[cfg(feature = "postgres-interop")]
pub type WithStorageSystem<'a> = dsl::EqAny<se::storage_system, Vec<&'a str>>;
#[cfg(feature = "postgres-interop")]
pub type ByRecords<'a> = dsl::Filter<Table, dsl::And<WithIndexes, WithStorageSystem<'a>>>;

#[cfg(feature = "postgres-interop")]
impl SfaEnclosure {
    pub fn all() -> Table {
        se::table
    }
    pub fn batch_upsert(x: Upserts<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all())
            .values(x.0)
            .on_conflict((se::index, se::storage_system))
            .do_update()
            .set((
                se::child_health_state.eq(excluded(se::child_health_state)),
                se::element_name.eq(excluded(se::element_name)),
                se::health_state.eq(excluded(se::health_state)),
                se::position.eq(excluded(se::position)),
                se::enclosure_type.eq(excluded(se::enclosure_type)),
            ))
    }
    fn batch_delete_filter<'a>(xs: Vec<&'a Self>) -> ByRecords<'a> {
        let (indexes, storage_systems): (Vec<_>, Vec<_>) = xs
            .into_iter()
            .map(|x| (x.index, x.storage_system.as_str()))
            .unzip();

        Self::all().filter(
            se::index
                .eq_any(indexes)
                .and(se::storage_system.eq_any(storage_systems)),
        )
    }
    pub fn batch_delete<'a>(xs: Vec<&'a Self>) -> impl Executable + 'a {
        diesel::delete(Self::batch_delete_filter(xs))
    }
}
