// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::input_document::{deserialize_input, SshOpts};
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
pub enum Input {
    SshCommand(SshCommand),
    SetupPlanesSsh(SetupPlanesSsh),
    SyncFileSsh(SyncFileSsh),
    CreateFileSsh(CreateFileSsh),
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum ActionName {
    SshCommand,
    SetupPlanesSsh,
    SyncFileSsh,
    CreateFileSsh,
}

impl Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::SshCommand => "ssh_command",
            Self::SetupPlanesSsh => "setup_planes_ssh",
            Self::SyncFileSsh => "sync_file_ssh",
            Self::CreateFileSsh => "create_file_ssh",
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
        ActionName::SshCommand => deserialize_input(input).map(Input::SshCommand),
        ActionName::SetupPlanesSsh => deserialize_input(input).map(Input::SetupPlanesSsh),
        ActionName::SyncFileSsh => deserialize_input(input).map(Input::SyncFileSsh),
        ActionName::CreateFileSsh => deserialize_input(input).map(Input::CreateFileSsh),
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct SshCommand {
    #[validate(length(min = 1))]
    pub(crate) host: String,
    pub(crate) run: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct SetupPlanesSsh {
    #[validate(length(min = 1))]
    pub(crate) hosts: Vec<String>,
    pub(crate) cp_addr: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct SyncFileSsh {
    #[validate(length(min = 1))]
    pub(crate) hosts: Vec<String>,
    pub(crate) from: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct CreateFileSsh {
    pub(crate) host: String,
    pub(crate) contents: String,
    pub(crate) path: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
}
