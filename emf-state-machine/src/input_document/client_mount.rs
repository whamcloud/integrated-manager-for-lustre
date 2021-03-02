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
pub enum Input {
    Create(Create),
    Unmount(Unmount),
    Mount(Mount),
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum ActionName {
    Create,
    Unmount,
    Mount,
}

impl fmt::Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::Create => "create",
            Self::Unmount => "unmount",
            Self::Mount => "mount",
        };

        write!(f, "{}", x)
    }
}

impl TryFrom<&str> for ActionName {
    type Error = io::Error;

    fn try_from(s: &str) -> Result<Self, Self::Error> {
        serde_json::from_str(&format!("\"{}\"", s)).map_err(|_| {
            io::Error::new(
                io::ErrorKind::InvalidInput,
                format!("{} is not a valid client mount action", s),
            )
        })
    }
}

pub(crate) fn get_input<'de, D>(action: ActionName, input: D) -> Result<Input, D::Error>
where
    D: Deserializer<'de>,
{
    match action {
        ActionName::Create => deserialize_input(input).map(Input::Create),
        ActionName::Mount => deserialize_input(input).map(Input::Mount),
        ActionName::Unmount => deserialize_input(input).map(Input::Unmount),
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Create {
    #[validate(length(min = 1))]
    pub(crate) hosts: Vec<String>,
    #[validate(length(min = 1))]
    pub(crate) mountspec: String,
    #[validate(length(min = 1))]
    pub(crate) mountpoint: String,
    pub(crate) tags: Option<Vec<String>>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Unmount {
    #[validate(length(min = 1))]
    host: String,
    #[validate(length(min = 1))]
    mountpoint: String,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Mount {
    #[validate(length(min = 1))]
    host: String,
    #[validate(length(min = 1))]
    mountpoint: String,
}
