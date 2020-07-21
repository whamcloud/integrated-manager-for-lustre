// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::{HealthState, MemberState};
#[cfg(feature = "postgres-interop")]
use crate::{schema::chroma_core_sfadiskdrive as sd, Executable, Upserts};
#[cfg(feature = "postgres-interop")]
use diesel::{
    self, dsl,
    pg::{upsert::excluded, Pg},
    prelude::*,
    Queryable,
};

#[cfg(feature = "postgres-interop")]
pub type Table = sd::table;
#[cfg(feature = "postgres-interop")]
pub type WithIndexes = dsl::EqAny<sd::index, Vec<i32>>;
#[cfg(feature = "postgres-interop")]
pub type WithStorageSystem<'a> = dsl::EqAny<sd::storage_system, Vec<&'a str>>;
#[cfg(feature = "postgres-interop")]
pub type ByRecords<'a> = dsl::Filter<Table, dsl::And<WithIndexes, WithStorageSystem<'a>>>;

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(Insertable, AsChangeset))]
#[cfg_attr(feature = "postgres-interop", table_name = "sd")]
pub struct SfaDiskDrive {
    pub index: i32,
    pub enclosure_index: i32,
    pub failed: bool,
    pub slot_number: i32,
    pub health_state: HealthState,
    pub health_state_reason: String,
    /// Specifies the member index of the disk drive.
    /// If the disk drive is not a member of a pool, this value will be not be set.
    pub member_index: Option<i16>,
    /// Specifies the state of the disk drive relative to a containing pool.
    pub member_state: MemberState,
    pub storage_system: String,
}

impl crate::Identifiable for SfaDiskDrive {
    type Id = String;

    fn id(&self) -> Self::Id {
        format!("{}_{}", self.index, self.storage_system)
    }
}

#[cfg(feature = "postgres-interop")]
impl Queryable<sd::SqlType, Pg> for SfaDiskDrive {
    type Row = (
        i32,
        i32,
        i32,
        bool,
        i32,
        HealthState,
        String,
        Option<i16>,
        MemberState,
        String,
    );

    fn build(row: Self::Row) -> Self {
        Self {
            index: row.1,
            enclosure_index: row.2,
            failed: row.3,
            slot_number: row.4,
            health_state: row.5,
            health_state_reason: row.6,
            member_index: row.7,
            member_state: row.8,
            storage_system: row.9,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl SfaDiskDrive {
    pub fn all() -> Table {
        sd::table
    }
    pub fn batch_upsert(x: Upserts<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all())
            .values(x.0)
            .on_conflict((sd::index, sd::storage_system))
            .do_update()
            .set((
                sd::failed.eq(excluded(sd::failed)),
                sd::health_state_reason.eq(excluded(sd::health_state_reason)),
                sd::health_state.eq(excluded(sd::health_state)),
                sd::member_index.eq(excluded(sd::member_index)),
                sd::member_state.eq(excluded(sd::member_state)),
                sd::enclosure_index.eq(excluded(sd::enclosure_index)),
            ))
    }
    fn batch_delete_filter<'a>(xs: Vec<&'a Self>) -> ByRecords<'a> {
        let (indexes, storage_systems): (Vec<_>, Vec<_>) = xs
            .into_iter()
            .map(|x| (x.index, x.storage_system.as_str()))
            .unzip();

        Self::all().filter(
            sd::index
                .eq_any(indexes)
                .and(sd::storage_system.eq_any(storage_systems)),
        )
    }
    pub fn batch_delete<'a>(xs: Vec<&'a Self>) -> impl Executable + 'a {
        diesel::delete(SfaDiskDrive::batch_delete_filter(xs))
    }
}
