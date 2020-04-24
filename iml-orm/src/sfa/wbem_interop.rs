// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::{
    EnclosureType, HealthState, MemberState, SfaDiskDrive, SfaEnclosure, SfaStorageSystem,
};
use std::convert::{TryFrom, TryInto};
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
    #[error("HealthState {0} not known")]
    UnknownHealth(String),
    #[error("Enclosure Type {0} not known")]
    UnknownEnclosure(String),
    #[error("MemberState {0} not known")]
    UnknownMemberState(String),
    #[error(transparent)]
    ParseBoolError(#[from] std::str::ParseBoolError),
    #[error(transparent)]
    ParseIntError(#[from] std::num::ParseIntError),
}

impl<'a> TryFrom<&'a str> for HealthState {
    type Error = SfaClassError;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s {
            "0" => Ok(HealthState::None),
            "1" => Ok(HealthState::Ok),
            "2" => Ok(HealthState::NonCritical),
            "3" => Ok(HealthState::Critical),
            "255" => Ok(HealthState::Unknown),
            x => Err(SfaClassError::UnknownHealth(x.into())),
        }
    }
}

impl<'a> TryFrom<&'a str> for EnclosureType {
    type Error = SfaClassError;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        match s {
            "0" => Ok(EnclosureType::None),
            "1" => Ok(EnclosureType::Disk),
            "2" => Ok(EnclosureType::Controller),
            "3" => Ok(EnclosureType::Ups),
            "255" => Ok(EnclosureType::Unknown),
            x => Err(SfaClassError::UnknownEnclosure(x.into())),
        }
    }
}

impl TryFrom<(String, Instance)> for SfaEnclosure {
    type Error = SfaClassError;

    fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
        if x.class_name != "DDN_SFAEnclosure" {
            return Err(SfaClassError::UnexpectedInstance(
                "DDN_SFAEnclosure",
                x.class_name.to_string(),
            ));
        }

        Ok(SfaEnclosure {
            index: x.try_get_property("Index")?.parse::<i32>()?,
            element_name: x.try_get_property("ElementName")?.into(),
            health_state: x.try_get_property("HealthState")?.try_into()?,
            health_state_reason: x.try_get_property("HealthStateReason")?.into(),
            position: x.try_get_property("Position")?.parse::<i16>()?,
            enclosure_type: x.try_get_property("Type")?.try_into()?,
            canister_location: x.try_get_property("CanisterLocation")?.into(),
            storage_system,
        })
    }
}

impl TryFrom<Instance> for SfaStorageSystem {
    type Error = SfaClassError;

    fn try_from(x: Instance) -> Result<Self, Self::Error> {
        if x.class_name != "DDN_SFAStorageSystem" {
            return Err(SfaClassError::UnexpectedInstance(
                "DDN_SFAStorageSystem",
                x.class_name.to_string(),
            ));
        }

        Ok(SfaStorageSystem {
            child_health_state: x.try_get_property("ChildHealthState")?.try_into()?,
            health_state_reason: x.try_get_property("HealthStateReason")?.into(),
            health_state: x.try_get_property("HealthState")?.try_into()?,
            uuid: x.try_get_property("UUID")?.into(),
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

impl<'a> TryFrom<&'a str> for MemberState {
    type Error = SfaClassError;

    fn try_from(x: &str) -> Result<Self, Self::Error> {
        match x {
            "0" => Ok(Self::MemberStateNormal),
            "1" => Ok(Self::MemberStateMissing),
            "2" => Ok(Self::MemberStateAlreadyMissing),
            "3" => Ok(Self::MemberStateRebuilding),
            "4" => Ok(Self::MemberStateWaitingToRebuild),
            "5" => Ok(Self::MemberStateFailed),
            "6" => Ok(Self::MemberStateMissingNoRebuild),
            "7" => Ok(Self::MemberStateErrorRec),
            "8" => Ok(Self::MemberStateUnassigned),
            "9" => Ok(Self::MemberStateCopyback),
            "10" => Ok(Self::MemberStateWaitingCopyback),
            "11" => Ok(Self::MemberStateLocked),
            "12" => Ok(Self::MemberStateLockedNoRebuild),
            "13" => Ok(Self::MemberStateAlreadyLocked),
            "14" => Ok(Self::MemberStateMissingPreventsRebuild),
            "15" => Ok(Self::MemberStateLockedPreventsRebuild),
            "255" => Ok(Self::MemberStateUnknown),
            x => Err(SfaClassError::UnknownMemberState(x.into())),
        }
    }
}

impl TryFrom<(String, Instance)> for SfaDiskDrive {
    type Error = SfaClassError;

    fn try_from((storage_system, x): (String, Instance)) -> Result<Self, Self::Error> {
        if x.class_name != "DDN_SFADiskDrive" {
            return Err(SfaClassError::UnexpectedInstance(
                "DDN_SFADiskDrive",
                x.class_name.to_string(),
            ));
        }

        Ok(SfaDiskDrive {
            index: x.try_get_property("Index")?.parse::<i32>()?,
            child_health_state: x.try_get_property("ChildHealthState")?.try_into()?,
            enclosure_index: x.try_get_property("EnclosureIndex")?.parse::<i32>()?,
            failed: x
                .try_get_property("Failed")?
                .to_lowercase()
                .parse::<bool>()?,
            health_state_reason: x.try_get_property("HealthStateReason")?.into(),
            health_state: x.try_get_property("HealthState")?.try_into()?,
            member_index: x
                .get_property("MemberIndex")
                .map(|x| x.parse::<i16>())
                .transpose()?,
            member_state: x.try_get_property("MemberState")?.try_into()?,
            slot_number: x.try_get_property("DiskSlotNumber")?.parse::<i32>()?,
            storage_system,
        })
    }
}
