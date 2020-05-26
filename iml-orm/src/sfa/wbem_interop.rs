// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::{
    SfaDiskDrive, SfaDiskSlot, SfaEnclosure, SfaJob, SfaPowerSupply, SfaStorageSystem,
};
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
            model: x.try_get_property("Model")?.into(),
            position: x.try_get_property("Position")?.parse::<i16>()?,
            enclosure_type: x.try_get_property("Type")?.parse::<i16>()?.try_into()?,
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
            child_health_state: x
                .try_get_property("ChildHealthState")?
                .parse::<i16>()?
                .try_into()?,
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
            job_type: x.try_get_property("JobType")?.parse::<i16>()?.try_into()?,
            state: x.try_get_property("JobState")?.parse::<i16>()?.try_into()?,
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
