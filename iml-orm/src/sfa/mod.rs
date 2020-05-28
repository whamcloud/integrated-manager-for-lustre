// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod disk_drive;
mod enclosure;
mod job;
mod power_supply;
mod storage_system;

#[cfg(feature = "wbem-interop")]
mod wbem_interop;

#[cfg(feature = "postgres-interop")]
use crate::schema::chroma_core_sfadiskslot;
pub use crate::sfa::{disk_drive::*, enclosure::*, job::*, power_supply::*, storage_system::*};
#[cfg(feature = "postgres-interop")]
use diesel::{
    backend::Backend,
    deserialize,
    serialize::{self, Output, ToSql},
    sql_types::SmallInt,
};
use serde_repr::{Deserialize_repr, Serialize_repr};
use std::{convert::TryFrom, io};
#[cfg(feature = "postgres-interop")]
use std::{convert::TryInto, io::Write};
#[cfg(feature = "wbem-interop")]
pub use wbem_interop::*;

#[derive(Serialize_repr, Deserialize_repr, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(
    feature = "postgres-interop",
    derive(AsExpression, SqlType, FromSqlRow)
)]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
#[cfg_attr(feature = "postgres-interop", postgres(type_name = "SmallInt"))]
#[repr(i16)]
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
impl<DB, ST> deserialize::FromSql<ST, DB> for EnclosureType
where
    DB: Backend,
    i16: deserialize::FromSql<ST, DB>,
{
    fn from_sql(bytes: Option<&DB::RawValue>) -> deserialize::Result<Self> {
        i16::from_sql(bytes)?
            .try_into()
            .map_err(|e: io::Error| e.into())
    }
}

#[derive(Serialize_repr, Deserialize_repr, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression, FromSqlRow))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
#[repr(i16)]
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
impl<DB, ST> deserialize::FromSql<ST, DB> for HealthState
where
    DB: Backend,
    i16: deserialize::FromSql<ST, DB>,
{
    fn from_sql(bytes: Option<&DB::RawValue>) -> deserialize::Result<Self> {
        i16::from_sql(bytes)?
            .try_into()
            .map_err(|e: io::Error| e.into())
    }
}

#[derive(Serialize_repr, Deserialize_repr, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression, FromSqlRow))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
#[repr(i16)]
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
impl<DB, ST> deserialize::FromSql<ST, DB> for JobType
where
    DB: Backend,
    i16: deserialize::FromSql<ST, DB>,
{
    fn from_sql(bytes: Option<&DB::RawValue>) -> deserialize::Result<Self> {
        i16::from_sql(bytes)?
            .try_into()
            .map_err(|e: io::Error| e.into())
    }
}

#[derive(Serialize_repr, Deserialize_repr, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression, FromSqlRow))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
#[repr(i16)]
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
impl<DB, ST> deserialize::FromSql<ST, DB> for JobState
where
    DB: Backend,
    i16: deserialize::FromSql<ST, DB>,
{
    fn from_sql(bytes: Option<&DB::RawValue>) -> deserialize::Result<Self> {
        i16::from_sql(bytes)?
            .try_into()
            .map_err(|e: io::Error| e.into())
    }
}

#[derive(Serialize_repr, Deserialize_repr, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression, FromSqlRow))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
#[repr(i16)]
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
impl<DB> ToSql<SmallInt, DB> for SubTargetType
where
    DB: Backend,
    i16: ToSql<SmallInt, DB>,
{
    fn to_sql<W: Write>(&self, out: &mut Output<W, DB>) -> serialize::Result {
        (*self as i16).to_sql(out)
    }
}

#[cfg(feature = "postgres-interop")]
impl<DB, ST> deserialize::FromSql<ST, DB> for SubTargetType
where
    DB: Backend,
    i16: deserialize::FromSql<ST, DB>,
{
    fn from_sql(bytes: Option<&DB::RawValue>) -> deserialize::Result<Self> {
        i16::from_sql(bytes)?
            .try_into()
            .map_err(|e: io::Error| e.into())
    }
}

#[derive(Serialize_repr, Deserialize_repr, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(AsExpression, FromSqlRow))]
#[cfg_attr(feature = "postgres-interop", sql_type = "SmallInt")]
#[repr(i16)]
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
impl<DB, ST> deserialize::FromSql<ST, DB> for MemberState
where
    DB: Backend,
    i16: deserialize::FromSql<ST, DB>,
{
    fn from_sql(bytes: Option<&DB::RawValue>) -> deserialize::Result<Self> {
        i16::from_sql(bytes)?
            .try_into()
            .map_err(|e: io::Error| e.into())
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(Insertable, AsChangeset))]
#[cfg_attr(feature = "postgres-interop", table_name = "chroma_core_sfadiskslot")]
pub struct SfaDiskSlot {
    pub index: i32,
    pub enclosure_index: i32,
    pub disk_drive_index: i32,
    pub storage_system: String,
}
