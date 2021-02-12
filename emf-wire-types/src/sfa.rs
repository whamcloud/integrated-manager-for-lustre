// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{Id, Name, TableName},
    Label,
};
use serde_repr::{Deserialize_repr, Serialize_repr};
use std::{convert::TryFrom, io};

#[cfg(feature = "wbem-interop")]
pub mod wbem_interop {
    use crate::sfa::{EnclosureType, HealthState, JobState, JobType, MemberState, SubTargetType};
    use emf_change::Identifiable;
    use std::{
        convert::{TryFrom, TryInto},
        io,
    };
    use thiserror::Error;
    use wbem_client::{
        resp::{Cim, IReturnValueInstance, Instance},
        CimXmlError,
    };

    #[derive(Error, Debug)]
    pub enum SfaClassError {
        #[error(transparent)]
        CimXmlError(#[from] CimXmlError),
        #[error("Expected class {0}, found class {1}")]
        UnexpectedInstance(&'static str, String),
        #[error(transparent)]
        IoError(#[from] io::Error),
        #[error(transparent)]
        ParseBoolError(#[from] std::str::ParseBoolError),
        #[error(transparent)]
        ParseIntError(#[from] std::num::ParseIntError),
    }

    #[derive(
        serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd,
    )]
    pub struct SfaDiskSlot {
        pub index: i32,
        pub enclosure_index: i32,
        pub disk_drive_index: i32,
        pub storage_system: String,
    }

    #[derive(
        serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd,
    )]
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

    impl Identifiable for SfaEnclosure {
        type Id = String;

        fn id(&self) -> Self::Id {
            format!("{}_{}", self.index, self.storage_system)
        }
    }

    impl TryFrom<(String, Instance)> for SfaEnclosure {
        type Error = SfaClassError;

        fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
            if x.class_name != "DDN_SFAEnclosure" {
                return Err(SfaClassError::UnexpectedInstance(
                    "DDN_SFAEnclosure",
                    x.class_name,
                ));
            }

            Ok(SfaEnclosure {
                index: x.try_get_property("Index")?.parse::<i32>()?,
                element_name: x.try_get_property("ElementName")?.into(),
                health_state: x
                    .try_get_property("HealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                health_state_reason: x.try_get_property("HealthStateReason")?.into(),
                child_health_state: x
                    .try_get_property("ChildHealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                model: x.try_get_property("Model")?.into(),
                position: x.try_get_property("Position")?.parse::<i16>()?,
                enclosure_type: x.try_get_property("Type")?.parse::<i16>()?.try_into()?,
                canister_location: x.try_get_property("CanisterLocation")?.into(),
                storage_system,
            })
        }
    }

    #[derive(Debug, Clone)]
    pub struct SfaStorageSystem {
        pub uuid: String,
        pub platform: String,
        pub health_state_reason: String,
        pub health_state: HealthState,
        pub child_health_state: HealthState,
    }

    impl TryFrom<Instance> for SfaStorageSystem {
        type Error = SfaClassError;

        fn try_from(x: Instance) -> Result<Self, Self::Error> {
            if x.class_name != "DDN_SFAStorageSystem" {
                return Err(SfaClassError::UnexpectedInstance(
                    "DDN_SFAStorageSystem",
                    x.class_name,
                ));
            }

            Ok(SfaStorageSystem {
                child_health_state: x
                    .try_get_property("ChildHealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                health_state_reason: x.try_get_property("HealthStateReason")?.into(),
                health_state: x
                    .try_get_property("HealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                uuid: x.try_get_property("UUID")?.into(),
                platform: x.try_get_property("Platform")?.into(),
            })
        }
    }

    impl TryFrom<Cim<IReturnValueInstance>> for SfaStorageSystem {
        type Error = SfaClassError;

        fn try_from(x: Cim<IReturnValueInstance>) -> Result<Self, Self::Error> {
            let x = x.message.simplersp.imethodresponse.i_return_value.instance;

            SfaStorageSystem::try_from(x)
        }
    }

    #[derive(
        serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd,
    )]
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

    impl Identifiable for SfaDiskDrive {
        type Id = String;

        fn id(&self) -> Self::Id {
            format!("{}_{}", self.index, self.storage_system)
        }
    }

    impl TryFrom<(String, Instance)> for SfaDiskDrive {
        type Error = SfaClassError;

        fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
            if x.class_name != "DDN_SFADiskDrive" {
                return Err(SfaClassError::UnexpectedInstance(
                    "DDN_SFADiskDrive",
                    x.class_name,
                ));
            }

            Ok(SfaDiskDrive {
                index: x.try_get_property("Index")?.parse::<i32>()?,
                enclosure_index: x.try_get_property("EnclosureIndex")?.parse::<i32>()?,
                failed: x
                    .try_get_property("Failed")?
                    .to_lowercase()
                    .parse::<bool>()?,
                health_state_reason: x.try_get_property("HealthStateReason")?.into(),
                health_state: x
                    .try_get_property("HealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                member_index: x
                    .get_property("MemberIndex")
                    .map(|x| x.parse::<i16>())
                    .transpose()?,
                member_state: x
                    .try_get_property("MemberState")?
                    .parse::<i16>()?
                    .try_into()?,
                slot_number: x.try_get_property("DiskSlotNumber")?.parse::<i32>()?,
                storage_system,
            })
        }
    }

    pub type SfaDiskDriveRow = (i32, i32, bool, i32, i16, String, Option<i16>, i16, String);

    impl From<SfaDiskDrive> for SfaDiskDriveRow {
        fn from(x: SfaDiskDrive) -> Self {
            let SfaDiskDrive {
                index,
                enclosure_index,
                failed,
                slot_number,
                health_state,
                health_state_reason,
                member_index,
                member_state,
                storage_system,
            } = x;

            (
                index,
                enclosure_index,
                failed,
                slot_number,
                health_state as i16,
                health_state_reason,
                member_index,
                member_state as i16,
                storage_system,
            )
        }
    }

    #[derive(
        serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd,
    )]
    pub struct SfaJob {
        pub index: i32,
        pub sub_target_index: Option<i32>,
        pub sub_target_type: Option<SubTargetType>,
        pub job_type: JobType,
        pub state: JobState,
        pub storage_system: String,
    }

    impl Identifiable for SfaJob {
        type Id = String;

        fn id(&self) -> Self::Id {
            format!("{}_{}", self.index, self.storage_system)
        }
    }

    pub type SfaJobRow = (i32, Option<i32>, Option<i16>, i16, i16, String);

    impl From<SfaJob> for SfaJobRow {
        fn from(x: SfaJob) -> Self {
            let SfaJob {
                index,
                sub_target_index,
                sub_target_type,
                job_type,
                state,
                storage_system,
            } = x;

            (
                index,
                sub_target_index,
                sub_target_type.map(|x| x as i16),
                job_type as i16,
                state as i16,
                storage_system,
            )
        }
    }

    impl TryFrom<(String, Instance)> for SfaJob {
        type Error = SfaClassError;

        fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
            if x.class_name != "DDN_SFAJob" {
                return Err(SfaClassError::UnexpectedInstance(
                    "DDN_SFAJob",
                    x.class_name,
                ));
            }

            Ok(SfaJob {
                index: x.try_get_property("Index")?.parse::<i32>()?,
                sub_target_index: x
                    .get_property("SubTargetIndex")
                    .map(|x| x.parse::<i32>())
                    .transpose()?,
                sub_target_type: x
                    .get_property("SubTargetType")
                    .map(|x| x.parse::<i16>())
                    .transpose()?
                    .map(|x| x.try_into())
                    .transpose()?,
                job_type: x.try_get_property("Type")?.parse::<i16>()?.try_into()?,
                state: x.try_get_property("State")?.parse::<i16>()?.try_into()?,
                storage_system,
            })
        }
    }

    impl TryFrom<(String, Instance)> for SfaDiskSlot {
        type Error = SfaClassError;

        fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
            if x.class_name != "DDN_SFADiskSlot" {
                return Err(SfaClassError::UnexpectedInstance(
                    "DDN_SFADiskSlot",
                    x.class_name,
                ));
            }

            Ok(SfaDiskSlot {
                index: x.try_get_property("Index")?.parse::<i32>()?,
                enclosure_index: x.try_get_property("EnclosureIndex")?.parse::<i32>()?,
                disk_drive_index: x.try_get_property("DiskDriveIndex")?.parse::<i32>()?,
                storage_system,
            })
        }
    }

    #[derive(
        serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd,
    )]
    pub struct SfaPowerSupply {
        pub index: i32,
        pub enclosure_index: i32,
        pub health_state: HealthState,
        pub health_state_reason: String,
        pub position: i16,
        pub storage_system: String,
    }

    pub type SfaPowerSupplyRow = (i32, i32, i16, String, i16, String);

    impl From<SfaPowerSupply> for SfaPowerSupplyRow {
        fn from(x: SfaPowerSupply) -> Self {
            let SfaPowerSupply {
                index,
                enclosure_index,
                health_state,
                health_state_reason,
                position,
                storage_system,
            } = x;

            (
                index,
                enclosure_index,
                health_state as i16,
                health_state_reason,
                position,
                storage_system,
            )
        }
    }

    impl Identifiable for SfaPowerSupply {
        type Id = String;

        fn id(&self) -> Self::Id {
            format!(
                "{}_{}_{}",
                self.index, self.storage_system, self.enclosure_index
            )
        }
    }

    impl TryFrom<(String, Instance)> for SfaPowerSupply {
        type Error = SfaClassError;

        fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
            if x.class_name != "DDN_SFAPowerSupply" {
                return Err(SfaClassError::UnexpectedInstance(
                    "DDN_SFAPowerSupply",
                    x.class_name,
                ));
            }

            Ok(SfaPowerSupply {
                index: x.try_get_property("Index")?.parse::<i32>()?,
                health_state_reason: x.try_get_property("HealthStateReason")?.into(),
                health_state: x
                    .try_get_property("HealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                position: x.try_get_property("Position")?.parse::<i16>()?,
                enclosure_index: x.try_get_property("EnclosureIndex")?.parse::<i32>()?,
                storage_system,
            })
        }
    }

    #[derive(
        serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq, Ord, PartialOrd,
    )]
    pub struct SfaController {
        pub index: i32,
        pub enclosure_index: i32,
        pub health_state: HealthState,
        pub health_state_reason: String,
        pub child_health_state: HealthState,
        pub storage_system: String,
    }

    impl Identifiable for SfaController {
        type Id = String;

        fn id(&self) -> Self::Id {
            format!("{}_{}", self.index, self.storage_system)
        }
    }

    pub type SfaControllerRow = (i32, i32, i16, String, i16, String);

    impl From<SfaController> for SfaControllerRow {
        fn from(x: SfaController) -> Self {
            let SfaController {
                index,
                enclosure_index,
                health_state,
                health_state_reason,
                child_health_state,
                storage_system,
            } = x;

            (
                index,
                enclosure_index,
                health_state as i16,
                health_state_reason,
                child_health_state as i16,
                storage_system,
            )
        }
    }

    impl TryFrom<(String, Instance)> for SfaController {
        type Error = SfaClassError;

        fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
            if x.class_name != "DDN_SFAController" {
                return Err(SfaClassError::UnexpectedInstance(
                    "DDN_SFAController",
                    x.class_name,
                ));
            }

            Ok(SfaController {
                index: x.try_get_property("Index")?.parse::<i32>()?,
                enclosure_index: x.try_get_property("EnclosureIndex")?.parse::<i32>()?,
                health_state_reason: x.try_get_property("HealthStateReason")?.into(),
                health_state: x
                    .try_get_property("HealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                child_health_state: x
                    .try_get_property("ChildHealthState")?
                    .parse::<i16>()?
                    .try_into()?,
                storage_system,
            })
        }
    }
}

#[derive(Serialize_repr, Deserialize_repr, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
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

#[repr(i16)]
#[derive(
    serde::Serialize, serde::Deserialize, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
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

#[repr(i16)]
#[derive(Serialize_repr, Deserialize_repr, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
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

#[derive(Serialize_repr, Deserialize_repr, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
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

#[derive(Serialize_repr, Deserialize_repr, Debug, Clone, Copy, PartialEq, Eq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
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

#[derive(Serialize_repr, Deserialize_repr, Debug, Copy, Clone, Eq, PartialEq, Ord, PartialOrd)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
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

/// Record from the `chroma_core_sfastoragesystem` table
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct SfaStorageSystem {
    pub id: i32,
    pub child_health_state: HealthState,
    pub health_state_reason: String,
    pub health_state: HealthState,
    pub uuid: String,
    pub platform: String,
}

pub const SFA_STORAGE_SYSTEM_TABLE_NAME: TableName = TableName("chroma_core_sfastoragesystem");

impl Name for SfaStorageSystem {
    fn table_name() -> TableName<'static> {
        SFA_STORAGE_SYSTEM_TABLE_NAME
    }
}

impl Id for SfaStorageSystem {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for SfaStorageSystem {
    fn label(&self) -> &str {
        "SFA Storage System"
    }
}

pub const SFA_ENCLOSURE_TABLE_NAME: TableName = TableName("chroma_core_sfaenclosure");

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct SfaEnclosure {
    pub id: i32,
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

impl Name for SfaEnclosure {
    fn table_name() -> TableName<'static> {
        SFA_ENCLOSURE_TABLE_NAME
    }
}

impl Id for SfaEnclosure {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for SfaEnclosure {
    fn label(&self) -> &str {
        "SFA enclosure"
    }
}

pub const SFA_DISK_DRIVE_TABLE_NAME: TableName = TableName("chroma_core_sfadiskdrive");

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct SfaDiskDrive {
    pub id: i32,
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

impl Name for SfaDiskDrive {
    fn table_name() -> TableName<'static> {
        SFA_DISK_DRIVE_TABLE_NAME
    }
}

impl Id for SfaDiskDrive {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for SfaDiskDrive {
    fn label(&self) -> &str {
        "SFA Disk Drive"
    }
}

pub const SFA_JOB_TABLE_NAME: TableName = TableName("chroma_core_sfajob");

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct SfaJob {
    pub id: i32,
    pub index: i32,
    pub sub_target_index: Option<i32>,
    pub sub_target_type: Option<SubTargetType>,
    pub job_type: JobType,
    pub state: JobState,
    pub storage_system: String,
}

impl Name for SfaJob {
    fn table_name() -> TableName<'static> {
        SFA_JOB_TABLE_NAME
    }
}

impl Id for SfaJob {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for SfaJob {
    fn label(&self) -> &str {
        "SFA Job"
    }
}

pub const SFA_POWER_SUPPLY_TABLE_NAME: TableName = TableName("chroma_core_sfapowersupply");

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct SfaPowerSupply {
    pub id: i32,
    pub index: i32,
    pub enclosure_index: i32,
    pub health_state: HealthState,
    pub health_state_reason: String,
    pub position: i16,
    pub storage_system: String,
}

impl Name for SfaPowerSupply {
    fn table_name() -> TableName<'static> {
        SFA_POWER_SUPPLY_TABLE_NAME
    }
}

impl Id for SfaPowerSupply {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for SfaPowerSupply {
    fn label(&self) -> &str {
        "SFA Power Supply"
    }
}

pub const SFA_CONTROLLER_TABLE_NAME: TableName = TableName("chroma_core_sfacontroller");

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct SfaController {
    pub id: i32,
    pub index: i32,
    pub enclosure_index: i32,
    pub health_state: HealthState,
    pub health_state_reason: String,
    pub child_health_state: HealthState,
    pub storage_system: String,
}

impl Name for SfaController {
    fn table_name() -> TableName<'static> {
        SFA_CONTROLLER_TABLE_NAME
    }
}

impl Id for SfaController {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for SfaController {
    fn label(&self) -> &str {
        "SFA Controller"
    }
}
