// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::cim_xml::resp::{Instance, Property};
use std::convert::{TryFrom, TryInto};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum SfaClassError {
    #[error("Expected class {0}, found class {1}")]
    UnexpectedInstance(&'static str, String),
    #[error("Property {0} not found")]
    PropertyNotfound(String),
    #[error("HealthState {0} not known")]
    UnknownHealth(String),
    #[error("Enclosure Type {0} not known")]
    UnknownEnclosure(String),
    #[error(transparent)]
    ParseIntError(#[from] std::num::ParseIntError),
}

#[derive(Debug)]
enum EnclosureType {
    None = 0,
    Disk = 1,
    Controller = 2,
    Ups = 3,
    Unknown = 255,
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

#[derive(Debug)]
enum HealthState {
    None = 0,
    Ok = 1,
    NonCritical = 2,
    Critical = 3,
    Unknown = 255,
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

#[derive(Debug)]
struct SfaEnclosure {
    element_name: String,
    health_state: HealthState,
    position: u8,
    enclosure_type: EnclosureType,
}

impl TryFrom<&Instance> for SfaEnclosure {
    type Error = SfaClassError;

    fn try_from(x: &Instance) -> Result<Self, Self::Error> {
        if x.class_name != "DDN_SFAEnclosure" {
            return Err(SfaClassError::UnexpectedInstance(
                "DDN_SFAEnclosure",
                x.class_name.to_string(),
            ));
        }

        Ok(SfaEnclosure {
            element_name: try_get_property("ElementName", &x.properties)?.into(),
            health_state: try_get_property("HealthState", &x.properties)?.try_into()?,
            position: try_get_property("Position", &x.properties)?.parse::<u8>()?,
            enclosure_type: try_get_property("Type", &x.properties)?.try_into()?,
        })
    }
}

fn try_get_property<'a>(name: &str, xs: &'a [Property]) -> Result<&'a str, SfaClassError> {
    get_property(name, xs).ok_or_else(|| SfaClassError::PropertyNotfound(name.into()))
}

fn get_property<'a>(name: &str, xs: &'a [Property]) -> Option<&'a str> {
    xs.into_iter()
        .find(|p| p.name() == Some(name))
        .and_then(|p| match p {
            Property::Single { value, .. } => value.as_deref(),
            _ => None,
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cim_xml::resp::Cim;

    #[test]
    fn test_sfa_enclosure() {
        let xml = include_bytes!("../fixtures/instance_list.xml");

        let r: Cim = quick_xml::de::from_str(std::str::from_utf8(xml).unwrap()).unwrap();

        let xs: Vec<_> = r
            .message
            .simplersp
            .imethodresponse
            .i_return_value
            .named_instance
            .iter()
            .map(|x| SfaEnclosure::try_from(&x.instance))
            .collect();

        insta::assert_debug_snapshot!(xs);
    }
}
