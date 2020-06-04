// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::HealthState;
#[cfg(feature = "postgres-interop")]
use crate::{schema::chroma_core_sfapowersupply as sp, Executable, Upserts};
#[cfg(feature = "postgres-interop")]
use diesel::{
    self, dsl,
    pg::{upsert::excluded, Pg},
    prelude::*,
    Queryable,
};

#[cfg(feature = "postgres-interop")]
pub type Table = sp::table;
#[cfg(feature = "postgres-interop")]
pub type WithIndexes = dsl::EqAny<sp::index, Vec<i32>>;
#[cfg(feature = "postgres-interop")]
pub type WithStorageSystem<'a> = dsl::EqAny<sp::storage_system, Vec<&'a str>>;
#[cfg(feature = "postgres-interop")]
pub type WithEnclosureIndex = dsl::EqAny<sp::enclosure_index, Vec<i32>>;
#[cfg(feature = "postgres-interop")]
pub type ByRecords<'a> =
    dsl::Filter<Table, dsl::And<WithEnclosureIndex, dsl::And<WithIndexes, WithStorageSystem<'a>>>>;

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(Insertable, AsChangeset))]
#[cfg_attr(feature = "postgres-interop", table_name = "sp")]
pub struct SfaPowerSupply {
    pub index: i32,
    pub enclosure_index: i32,
    pub health_state: HealthState,
    pub health_state_reason: String,
    pub position: i16,
    pub storage_system: String,
}

impl crate::Identifiable for SfaPowerSupply {
    type Id = String;

    fn id(&self) -> Self::Id {
        format!(
            "{}_{}_{}",
            self.index, self.storage_system, self.enclosure_index
        )
    }
}

#[cfg(feature = "postgres-interop")]
impl Queryable<sp::SqlType, Pg> for SfaPowerSupply {
    type Row = (i32, i32, i32, HealthState, String, i16, String);

    fn build(row: Self::Row) -> Self {
        Self {
            index: row.1,
            enclosure_index: row.2,
            health_state: row.3,
            health_state_reason: row.4,
            position: row.5,
            storage_system: row.6,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl SfaPowerSupply {
    pub fn all() -> Table {
        sp::table
    }
    pub fn batch_upsert(x: Upserts<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all())
            .values(x.0)
            .on_conflict((sp::index, sp::storage_system, sp::enclosure_index))
            .do_update()
            .set((
                sp::health_state.eq(excluded(sp::health_state)),
                sp::health_state_reason.eq(excluded(sp::health_state_reason)),
                sp::position.eq(excluded(sp::position)),
            ))
    }
    fn batch_delete_filter<'a>(xs: Vec<&'a Self>) -> ByRecords<'a> {
        let (enclosure_indexes, b): (Vec<_>, Vec<_>) = xs
            .into_iter()
            .map(|x| (x.enclosure_index, (x.index, x.storage_system.as_str())))
            .unzip();

        let (indexes, storage_systems): (Vec<_>, Vec<_>) = b.into_iter().unzip();

        Self::all().filter(
            sp::enclosure_index.eq_any(enclosure_indexes).and(
                sp::index
                    .eq_any(indexes)
                    .and(sp::storage_system.eq_any(storage_systems)),
            ),
        )
    }
    pub fn batch_delete<'a>(xs: Vec<&'a Self>) -> impl Executable + 'a {
        diesel::delete(Self::batch_delete_filter(xs))
    }
}
