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
    Mounted,
    Unmounted,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(untagged)]
pub(crate) enum Input {
    Format(Format),
    Mount(Mount),
    Unmount(Unmount),
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ActionName {
    Format,
    Mount,
    Unmount,
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
            Self::Format => write!(f, "Format"),
            Self::Mount => write!(f, "Mount"),
            Self::Unmount => write!(f, "Unmount"),
        }
    }
}

pub(crate) fn get_input<'de, D>(action: ActionName, input: D) -> Result<Input, D::Error>
where
    D: Deserializer<'de>,
{
    match action {
        ActionName::Format => deserialize_input(input).map(Input::Format),
        ActionName::Mount => deserialize_input(input).map(Input::Mount),
        ActionName::Unmount => deserialize_input(input).map(Input::Unmount),
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Format {
    #[validate(length(min = 1))]
    host: String,
    #[validate(length(min = 1))]
    name: String,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Mount {
    #[validate(length(min = 1))]
    host: String,
    #[validate(length(min = 1))]
    name: String,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Unmount {
    #[validate(length(min = 1))]
    host: String,
    #[validate(length(min = 1))]
    name: String,
}
