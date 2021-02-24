// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::input_document::deserialize_input;
use serde::Deserializer;
use std::{convert::TryFrom, fmt, io};
use validator::Validate;

#[derive(
    PartialEq, Eq, Clone, Copy, Debug, PartialOrd, Ord, serde::Serialize, serde::Deserialize, Hash,
)]
#[serde(rename_all = "snake_case")]
pub(crate) enum State {
    Unavailable,
    Available,
    Started,
    Stopped,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(untagged)]
pub(crate) enum Input {
    Start(Start),
    Stop(Stop),
    Create(Create),
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ActionName {
    Start,
    Stop,
    Create,
}

impl TryFrom<&str> for ActionName {
    type Error = io::Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        serde_json::from_str(&format!("\"{}\"", s)).map_err(|_| {
            io::Error::new(
                io::ErrorKind::InvalidInput,
                format!("{} is not a valid host action", s),
            )
        })
    }
}

impl fmt::Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Start => write!(f, "Start"),
            Self::Stop => write!(f, "Stop"),
            Self::Create => write!(f, "Create"),
        }
    }
}

pub(crate) fn get_input<'de, D>(action: ActionName, input: D) -> Result<Input, D::Error>
where
    D: Deserializer<'de>,
{
    match action {
        ActionName::Start => deserialize_input(input).map(Input::Start),
        ActionName::Stop => deserialize_input(input).map(Input::Stop),
        ActionName::Create => deserialize_input(input).map(Input::Create),
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Start {
    #[validate(length(min = 1))]
    name: String,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Stop {
    #[validate(length(min = 1))]
    name: String,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MgtType {
    Volume,
    Target,
    Combined,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Create {
    #[validate(length(min = 1))]
    ost_volumes: Vec<String>,
    #[validate(length(min = 1))]
    name: String,
    mgt_type: MgtType,
    #[validate(length(min = 1))]
    mgt: String,
    #[validate(length(min = 1))]
    mdt_volumes: Vec<String>,
}
