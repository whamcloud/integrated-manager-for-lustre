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
        chroma_core_sfapowersupply, chroma_core_sfastoragesystem as ss,
        chroma_core_sfastoragesystem,
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
use std::{convert::TryFrom, io};
#[cfg(feature = "postgres-interop")]
use std::{convert::TryInto, io::Write};
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

impl Default for EnclosureType {
    fn default() -> Self {
        Self::Unknown
    }
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

impl TryFrom<i16> for EnclosureType {
    type Error = io::Error;

    fn try_from(x: i16) -> Result<Self, Self::Error> {
        match x {
            0 => Ok(Self::None),
            1 => Ok(Self::Disk),
            2 => Ok(Self::Controller),
            3 => Ok(Self::Ups),
            255 => Ok(Self::Unknown),
            x => Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Unknown EnclosureType {:?}", x),
            )),
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
        i16::build(row).try_into().unwrap_or_default()
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

impl Default for HealthState {
    fn default() -> Self {
        Self::Unknown
    }
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

impl TryFrom<i16> for HealthState {
    type Error = io::Error;

    fn try_from(s: i16) -> Result<Self, Self::Error> {
        match s {
            0 => Ok(Self::None),
            1 => Ok(Self::Ok),
            2 => Ok(Self::NonCritical),
            3 => Ok(Self::Critical),
            255 => Ok(Self::Unknown),
            x => Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Unknown HealthState {:?}", x),
            )),
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
        i16::build(row).try_into().unwrap_or_default()
    }
}

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum JobType {
    Initialize = 0,
    Rebuild = 1,
    RebuildFract = 2,
    RebuildDist = 3,
    Erase = 4,
    Delete = 5,
    Failover = 6,
    Move = 7,
    Migrate = 8,
    Verify = 9,
    VerifyForce = 10,
    VerifyOnce = 11,
    VerifyNoCorrect = 12,
    NonDestructiveInitialize = 13,
    Copyback = 14,
    RebuildFast = 15,
    Failback = 16,
    RebuildMixed = 17,
    Unknown = 255,
}

impl Default for JobType {
    fn default() -> Self {
        Self::Unknown
    }
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

impl TryFrom<i16> for JobType {
    type Error = io::Error;

    fn try_from(x: i16) -> Result<Self, Self::Error> {
        match x {
            0 => Ok(Self::Initialize),
            1 => Ok(Self::Rebuild),
            2 => Ok(Self::RebuildFract),
            3 => Ok(Self::RebuildDist),
            4 => Ok(Self::Erase),
            5 => Ok(Self::Delete),
            6 => Ok(Self::Failover),
            7 => Ok(Self::Move),
            8 => Ok(Self::Migrate),
            9 => Ok(Self::Verify),
            10 => Ok(Self::VerifyForce),
            11 => Ok(Self::VerifyOnce),
            12 => Ok(Self::VerifyNoCorrect),
            13 => Ok(Self::NonDestructiveInitialize),
            14 => Ok(Self::Copyback),
            15 => Ok(Self::RebuildFast),
            16 => Ok(Self::Failback),
            17 => Ok(Self::RebuildMixed),
            255 => Ok(Self::Unknown),
            x => Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Unknown JobType {:?}", x),
            )),
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
        i16::build(row).try_into().unwrap_or_default()
    }
}
#[derive(
    serde::Serialize, serde::Deserialize, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum JobState {
    Queued = 0,
    Running = 1,
    Paused = 2,
    Suspended = 3,
    Completed = 4,
    NoSpares = 5,
    Unknown = 255,
}

impl Default for JobState {
    fn default() -> Self {
        Self::Unknown
    }
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

impl TryFrom<i16> for JobState {
    type Error = io::Error;

    fn try_from(x: i16) -> Result<Self, Self::Error> {
        match x {
            0 => Ok(Self::Queued),
            1 => Ok(Self::Running),
            2 => Ok(Self::Paused),
            3 => Ok(Self::Suspended),
            4 => Ok(Self::Completed),
            5 => Ok(Self::NoSpares),
            255 => Ok(Self::Unknown),
            x => Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Unknown JobState {:?}", x),
            )),
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
        i16::build(row).try_into().unwrap_or_default()
    }
}

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum SubTargetType {
    Pool = 0,
    Vd = 1,
    Pd = 2,
    Unknown = 255,
}

impl Default for SubTargetType {
    fn default() -> Self {
        Self::Unknown
    }
}

impl TryFrom<i16> for SubTargetType {
    type Error = io::Error;

    fn try_from(x: i16) -> Result<Self, Self::Error> {
        match x {
            0 => Ok(Self::Pool),
            1 => Ok(Self::Vd),
            2 => Ok(Self::Pd),
            255 => Ok(Self::Unknown),
            x => Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Unknown SubTargetType {:?}", x),
            )),
        }
    }
}

#[cfg(feature = "postgres-interop")]
impl<DB, ST> Queryable<ST, DB> for SubTargetType
where
    DB: Backend,
    i16: Queryable<ST, DB>,
{
    type Row = <i16 as Queryable<ST, DB>>::Row;

    fn build(row: Self::Row) -> Self {
        i16::build(row).try_into().unwrap_or_default()
    }
}

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
pub enum MemberState {
    Normal = 0,
    Missing = 1,
    AlreadyMissing = 2,
    Rebuilding = 3,
    WaitingToRebuild = 4,
    Failed = 5,
    MissingNoRebuild = 6,
    ErrorRec = 7,
    Unassigned = 8,
    Copyback = 9,
    WaitingCopyback = 10,
    Locked = 11,
    LockedNoRebuild = 12,
    AlreadyLocked = 13,
    MissingPreventsRebuild = 14,
    LockedPreventsRebuild = 15,
    Unknown = 255,
}

impl Default for MemberState {
    fn default() -> Self {
        Self::Unknown
    }
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

impl TryFrom<i16> for MemberState {
    type Error = io::Error;

    fn try_from(x: i16) -> Result<Self, Self::Error> {
        match x {
            0 => Ok(Self::Normal),
            1 => Ok(Self::Missing),
            2 => Ok(Self::AlreadyMissing),
            3 => Ok(Self::Rebuilding),
            4 => Ok(Self::WaitingToRebuild),
            5 => Ok(Self::Failed),
            6 => Ok(Self::MissingNoRebuild),
            7 => Ok(Self::ErrorRec),
            8 => Ok(Self::Unassigned),
            9 => Ok(Self::Copyback),
            10 => Ok(Self::WaitingCopyback),
            11 => Ok(Self::Locked),
            12 => Ok(Self::LockedNoRebuild),
            13 => Ok(Self::AlreadyLocked),
            14 => Ok(Self::MissingPreventsRebuild),
            15 => Ok(Self::LockedPreventsRebuild),
            255 => Ok(Self::Unknown),
            x => Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Unknown MemberState {:?}", x),
            )),
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
        i16::build(row).try_into().unwrap_or_default()
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
    pub model: String,
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
    pub sub_target_type: Option<SubTargetType>,
    pub job_type: JobType,
    pub state: JobState,
    pub storage_system: String,
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(
    feature = "postgres-interop",
    derive(Queryable, Insertable, AsChangeset)
)]
#[cfg_attr(feature = "postgres-interop", primary_key(index))]
#[cfg_attr(
    feature = "postgres-interop",
    table_name = "chroma_core_sfapowersupply"
)]
pub struct SfaPowerSupply {
    pub index: i32,
    pub health_state: HealthState,
    pub health_state_reason: String,
    pub position: i16,
    pub enclosure_index: i32,
    pub storage_system: String,
}
