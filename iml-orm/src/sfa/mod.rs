// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[cfg(feature = "tokio-postgres-interop")]
mod tokio_postgres_interop;
#[cfg(feature = "wbem-interop")]
mod wbem_interop;

#[cfg(feature = "postgres-interop")]
use crate::{
    schema::{
        chroma_core_sfadiskdrive as sd, chroma_core_sfadiskdrive, chroma_core_sfadiskslot,
        chroma_core_sfaenclosure as se, chroma_core_sfaenclosure, chroma_core_sfajob,
        chroma_core_sfastoragesystem as ss, chroma_core_sfastoragesystem,
    },
    Additions, Executable, Updates,
};
#[cfg(feature = "postgres-interop")]
use diesel::{
    self,
    backend::Backend,
    serialize::{self, Output, ToSql},
    sql_types::SmallInt,
    Queryable,
};
#[cfg(feature = "postgres-interop")]
use diesel::{pg::upsert::excluded, prelude::*};
#[cfg(feature = "postgres-interop")]
use std::io::Write;
#[cfg(feature = "tokio-postgres-interop")]
pub use tokio_postgres_interop::*;
#[cfg(feature = "wbem-interop")]
pub use wbem_interop::*;

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression, SqlType))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
#[cfg_attr(feature = "postgres-interop", postgres(type_name = "SmallInt"))]
pub enum EnclosureType {
    None = 0,
    Disk = 1,
    Controller = 2,
    Ups = 3,
    Unknown = 255,
}

#[cfg(feature = "postgres-interop")]
impl<DB> ToSql<SmallInt, DB> for EnclosureType
where
    DB: Backend,
    i16: ToSql<SmallInt, DB>,
{
    fn to_sql<W: Write>(&self, out: &mut Output<W, DB>) -> serialize::Result {
        (*self as i16).to_sql(out)
    }
}

impl From<i16> for EnclosureType {
    fn from(x: i16) -> Self {
        match x {
            0 => Self::None,
            1 => Self::Disk,
            2 => Self::Controller,
            3 => Self::Ups,
            _ => Self::Unknown,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl<DB, ST> Queryable<ST, DB> for EnclosureType
where
    DB: Backend,
    i16: Queryable<ST, DB>,
{
    type Row = <i16 as Queryable<ST, DB>>::Row;

    fn build(row: Self::Row) -> Self {
        i16::build(row).into()
    }
}

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum HealthState {
    None = 0,
    Ok = 1,
    NonCritical = 2,
    Critical = 3,
    Unknown = 255,
}

#[cfg(feature = "postgres-interop")]
impl<DB> ToSql<SmallInt, DB> for HealthState
where
    DB: Backend,
    i16: ToSql<SmallInt, DB>,
{
    fn to_sql<W: Write>(&self, out: &mut Output<W, DB>) -> serialize::Result {
        (*self as i16).to_sql(out)
    }
}

impl From<i16> for HealthState {
    fn from(x: i16) -> Self {
        match x {
            0 => Self::None,
            1 => Self::Ok,
            2 => Self::NonCritical,
            3 => Self::Critical,
            _ => Self::Unknown,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl<DB, ST> Queryable<ST, DB> for HealthState
where
    DB: Backend,
    i16: Queryable<ST, DB>,
{
    type Row = <i16 as Queryable<ST, DB>>::Row;

    fn build(row: Self::Row) -> Self {
        i16::build(row).into()
    }
}

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum JobType {
    TypeInitialize = 0,
    TypeRebuild = 1,
    TypeRebuildFract = 2,
    TypeRebuildDist = 3,
    TypeErase = 4,
    TypeDelete = 5,
    TypeFailover = 6,
    TypeMove = 7,
    TypeMigrate = 8,
    TypeVerify = 9,
    TypeVerifyForce = 10,
    TypeVerifyOnce = 11,
    TypeVerifyNoCorrect = 12,
    TypeNonDestructiveInitialize = 13,
    TypeCopyback = 14,
    TypeRebuildFast = 15,
    TypeFailback = 16,
    TypeRebuildMixed = 17,
    TypeUnknown = 255,
}

#[cfg(feature = "postgres-interop")]
impl<DB> ToSql<SmallInt, DB> for JobType
where
    DB: Backend,
    i16: ToSql<SmallInt, DB>,
{
    fn to_sql<W: Write>(&self, out: &mut Output<W, DB>) -> serialize::Result {
        (*self as i16).to_sql(out)
    }
}

impl From<i16> for JobType {
    fn from(x: i16) -> Self {
        match x {
            0 => Self::TypeInitialize,
            1 => Self::TypeRebuild,
            2 => Self::TypeRebuildFract,
            3 => Self::TypeRebuildDist,
            4 => Self::TypeErase,
            5 => Self::TypeDelete,
            6 => Self::TypeFailover,
            7 => Self::TypeMove,
            8 => Self::TypeMigrate,
            9 => Self::TypeVerify,
            10 => Self::TypeVerifyForce,
            11 => Self::TypeVerifyOnce,
            12 => Self::TypeVerifyNoCorrect,
            13 => Self::TypeNonDestructiveInitialize,
            14 => Self::TypeCopyback,
            15 => Self::TypeRebuildFast,
            16 => Self::TypeFailback,
            17 => Self::TypeRebuildMixed,
            _ => Self::TypeUnknown,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl<DB, ST> Queryable<ST, DB> for JobType
where
    DB: Backend,
    i16: Queryable<ST, DB>,
{
    type Row = <i16 as Queryable<ST, DB>>::Row;

    fn build(row: Self::Row) -> Self {
        i16::build(row).into()
    }
}
#[derive(
    serde::Serialize, serde::Deserialize, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum JobState {
    StateQueued = 0,
    StateRunning = 1,
    StatePaused = 2,
    StateSuspended = 3,
    StateCompleted = 4,
    StateNoSpares = 5,
    StateUnknown = 255,
}

#[cfg(feature = "postgres-interop")]
impl<DB> ToSql<SmallInt, DB> for JobState
where
    DB: Backend,
    i16: ToSql<SmallInt, DB>,
{
    fn to_sql<W: Write>(&self, out: &mut Output<W, DB>) -> serialize::Result {
        (*self as i16).to_sql(out)
    }
}

impl From<i16> for JobState {
    fn from(x: i16) -> Self {
        match x {
            0 => Self::StateQueued,
            1 => Self::StateRunning,
            2 => Self::StatePaused,
            3 => Self::StateSuspended,
            4 => Self::StateCompleted,
            5 => Self::StateNoSpares,
            _ => Self::StateUnknown,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl<DB, ST> Queryable<ST, DB> for JobState
where
    DB: Backend,
    i16: Queryable<ST, DB>,
{
    type Row = <i16 as Queryable<ST, DB>>::Row;

    fn build(row: Self::Row) -> Self {
        i16::build(row).into()
    }
}

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum MemberState {
    MemberStateNormal = 0,
    MemberStateMissing = 1,
    MemberStateAlreadyMissing = 2,
    MemberStateRebuilding = 3,
    MemberStateWaitingToRebuild = 4,
    MemberStateFailed = 5,
    MemberStateMissingNoRebuild = 6,
    MemberStateErrorRec = 7,
    MemberStateUnassigned = 8,
    MemberStateCopyback = 9,
    MemberStateWaitingCopyback = 10,
    MemberStateLocked = 11,
    MemberStateLockedNoRebuild = 12,
    MemberStateAlreadyLocked = 13,
    MemberStateMissingPreventsRebuild = 14,
    MemberStateLockedPreventsRebuild = 15,
    MemberStateUnknown = 255,
}

#[cfg(feature = "postgres-interop")]
impl<DB> ToSql<SmallInt, DB> for MemberState
where
    DB: Backend,
    i16: ToSql<SmallInt, DB>,
{
    fn to_sql<W: Write>(&self, out: &mut Output<W, DB>) -> serialize::Result {
        (*self as i16).to_sql(out)
    }
}

impl From<i16> for MemberState {
    fn from(x: i16) -> Self {
        match x {
            0 => Self::MemberStateNormal,
            1 => Self::MemberStateMissing,
            2 => Self::MemberStateAlreadyMissing,
            3 => Self::MemberStateRebuilding,
            4 => Self::MemberStateWaitingToRebuild,
            5 => Self::MemberStateFailed,
            6 => Self::MemberStateMissingNoRebuild,
            7 => Self::MemberStateErrorRec,
            8 => Self::MemberStateUnassigned,
            9 => Self::MemberStateCopyback,
            10 => Self::MemberStateWaitingCopyback,
            11 => Self::MemberStateLocked,
            12 => Self::MemberStateLockedNoRebuild,
            13 => Self::MemberStateAlreadyLocked,
            14 => Self::MemberStateMissingPreventsRebuild,
            15 => Self::MemberStateLockedPreventsRebuild,
            _ => Self::MemberStateUnknown,
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl<DB, ST> Queryable<ST, DB> for MemberState
where
    DB: Backend,
    i16: Queryable<ST, DB>,
{
    type Row = <i16 as Queryable<ST, DB>>::Row;

    fn build(row: Self::Row) -> Self {
        i16::build(row).into()
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(
    feature = "postgres-interop",
    derive(Queryable, Insertable, AsChangeset, Identifiable)
)]
#[cfg_attr(feature = "postgres-interop", primary_key(index))]
#[cfg_attr(feature = "postgres-interop", table_name = "chroma_core_sfaenclosure")]
pub struct SfaEnclosure {
    /// Specifies the index, part of the OID, of the enclosure.
    pub index: i32,
    pub element_name: String,
    pub health_state: HealthState,
    pub health_state_reason: String,
    pub position: i16,
    pub enclosure_type: EnclosureType,
    pub canister_location: String,
    pub storage_system: String,
}

#[cfg(feature = "postgres-interop")]
pub type Table = se::table;

#[cfg(feature = "postgres-interop")]
impl SfaEnclosure {
    pub fn all() -> Table {
        se::table
    }
    pub fn batch_insert(x: Additions<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all()).values(x.0)
    }
    pub fn batch_upsert(x: Updates<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all())
            .values(x.0)
            .on_conflict(se::index)
            .do_update()
            .set((
                se::element_name.eq(excluded(se::element_name)),
                se::health_state.eq(excluded(se::health_state)),
                se::position.eq(excluded(se::position)),
                se::enclosure_type.eq(excluded(se::enclosure_type)),
                se::storage_system.eq(excluded(se::storage_system)),
            ))
    }
    pub fn batch_remove(xs: Vec<i32>) -> impl Executable {
        diesel::delete(Self::all()).filter(se::index.eq_any(xs))
    }
}

#[derive(Debug, Clone)]
#[cfg_attr(
    feature = "postgres-interop",
    derive(Queryable, Insertable, AsChangeset)
)]
#[cfg_attr(
    feature = "postgres-interop",
    table_name = "chroma_core_sfastoragesystem"
)]
pub struct SfaStorageSystem {
    pub child_health_state: HealthState,
    pub health_state_reason: String,
    pub health_state: HealthState,
    pub uuid: String,
}

#[cfg(feature = "postgres-interop")]
impl SfaStorageSystem {
    pub fn upsert(x: Self) -> impl Executable {
        diesel::insert_into(ss::table)
            .values(x.clone())
            .on_conflict(ss::uuid)
            .do_update()
            .set(x)
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(
    feature = "postgres-interop",
    derive(Queryable, Insertable, AsChangeset)
)]
#[cfg_attr(feature = "postgres-interop", primary_key(index))]
#[cfg_attr(feature = "postgres-interop", table_name = "chroma_core_sfadiskdrive")]
pub struct SfaDiskDrive {
    pub index: i32,
    pub child_health_state: HealthState,
    pub failed: bool,
    pub slot_number: i32,
    pub health_state: HealthState,
    pub health_state_reason: String,
    /// Specifies the member index of the disk drive.
    /// If the disk drive is not a member of a pool, this value will be not be set.
    pub member_index: Option<i16>,
    /// Specifies the state of the disk drive relative to a containing pool.
    pub member_state: MemberState,
    pub enclosure_index: i32,
    pub storage_system: String,
}

#[cfg(feature = "postgres-interop")]
impl SfaDiskDrive {
    pub fn all() -> sd::table {
        sd::table
    }
    pub fn batch_insert(x: Additions<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all()).values(x.0)
    }
    pub fn batch_upsert(x: Updates<&Self>) -> impl Executable + '_ {
        diesel::insert_into(Self::all())
            .values(x.0)
            .on_conflict(sd::index)
            .do_update()
            .set((
                sd::child_health_state.eq(excluded(sd::child_health_state)),
                sd::failed.eq(excluded(sd::failed)),
                sd::health_state_reason.eq(excluded(sd::health_state_reason)),
                sd::health_state.eq(excluded(sd::health_state)),
                sd::member_index.eq(excluded(sd::member_index)),
                sd::member_state.eq(excluded(sd::member_state)),
                sd::enclosure_index.eq(excluded(sd::enclosure_index)),
            ))
    }
    pub fn batch_remove(xs: Vec<i32>) -> impl Executable {
        diesel::delete(Self::all()).filter(sd::index.eq_any(xs))
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(
    feature = "postgres-interop",
    derive(Queryable, Insertable, AsChangeset)
)]
#[cfg_attr(feature = "postgres-interop", primary_key(index))]
#[cfg_attr(feature = "postgres-interop", table_name = "chroma_core_sfadiskslot")]
pub struct SfaDiskSlot {
    pub index: i32,
    pub enclosure_index: i32,
    pub disk_drive_index: i32,
    pub storage_system: String,
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(
    feature = "postgres-interop",
    derive(Queryable, Insertable, AsChangeset)
)]
#[cfg_attr(feature = "postgres-interop", primary_key(index))]
#[cfg_attr(feature = "postgres-interop", table_name = "chroma_core_sfajob")]
pub struct SfaJob {
    pub index: i32,
    pub sub_target_index: Option<i32>,
    pub sub_target_type: Option<i16>,
    pub job_type: JobType,
    pub state: JobState,
    pub storage_system: String,
}
