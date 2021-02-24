// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::input_document::deserialize_input;
use serde::Deserializer;
use std::{
    convert::TryFrom,
    fmt::{self, Display},
    io,
};
use validator::Validate;

#[derive(
    Clone, Copy, Debug, Eq, PartialEq, PartialOrd, Hash, Ord, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub(crate) enum State {
    Up,
    Down,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(untagged)]
pub(crate) enum Input {
    Add(Add),
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ActionName {
    Add,
}

impl Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::Add => "add",
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
        ActionName::Add => deserialize_input(input).map(Input::Add),
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct Add {
    #[validate(length(min = 1))]
    hosts: Vec<String>,
    auth: Option<String>,
    user: Option<String>,
    tags: Option<Vec<String>>,
}
