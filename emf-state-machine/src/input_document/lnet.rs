// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::input_document::{deserialize_input, NullInput};
use serde::Deserializer;
use std::{convert::TryFrom, fmt, io};
use validator::Validate;

#[derive(
    PartialEq, Eq, Clone, Copy, Debug, PartialOrd, Ord, serde::Serialize, serde::Deserialize, Hash,
)]
#[serde(rename_all = "snake_case")]
pub(crate) enum State {
    Up,
    Down,
    Loaded,
    Unloaded,
    Configured,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(untagged)]
pub(crate) enum Input {
    Start(NullInput),
    Stop(NullInput),
    Load(NullInput),
    Unload(NullInput),
    Configure(Configure),
    Export(NullInput),
    Unconfigure(NullInput),
    Import(NullInput),
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ActionName {
    Start,
    Stop,
    Load,
    Unload,
    Configure,
    Export,
    Unconfigure,
    Import,
}

impl fmt::Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::Start => "start",
            Self::Stop => "stop",
            Self::Load => "load",
            Self::Unload => "unload",
            Self::Configure => "configure",
            Self::Export => "export",
            Self::Unconfigure => "unconfigure",
            Self::Import => "import",
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
                format!("{} is not a valid host action", s),
            )
        })
    }
}

pub(crate) fn get_input<'de, D>(action: ActionName, input: D) -> Result<Input, D::Error>
where
    D: Deserializer<'de>,
{
    match action {
        ActionName::Start => deserialize_input(input).map(Input::Start),
        ActionName::Stop => deserialize_input(input).map(Input::Stop),
        ActionName::Load => deserialize_input(input).map(Input::Load),
        ActionName::Unload => deserialize_input(input).map(Input::Unload),
        ActionName::Configure => deserialize_input(input).map(Input::Configure),
        ActionName::Export => deserialize_input(input).map(Input::Export),
        ActionName::Unconfigure => deserialize_input(input).map(Input::Unconfigure),
        ActionName::Import => deserialize_input(input).map(Input::Import),
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Configure {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
    #[validate(length(min = 1))]
    network: String,
    #[validate(length(min = 1))]
    ethernet: String,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
pub struct Unconfigure {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
pub struct Start {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
pub struct Stop {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
pub struct Load {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
pub struct Unload {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
pub struct Export {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
pub struct Import {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
    #[validate(length(min = 1))]
    filepath: String,
}
