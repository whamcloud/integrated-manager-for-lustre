// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::input_document::{deserialize_input, SshOpts};
use serde::Deserializer;
use std::{
    convert::TryFrom,
    fmt::{self, Display},
    io,
    time::Duration,
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
    ChmodSsh(ChmodSsh),
    ConfigureIfConfigSsh(ConfigureIfConfigSsh),
    ConfigureNetworkSsh(ConfigureNetworkSsh),
    CreateFileSsh(CreateFileSsh),
    IsAvailable(IsAvailable),
    SetupPlanesSsh(SetupPlanesSsh),
    SshCommand(SshCommand),
    SyncFileSsh(SyncFileSsh),
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum ActionName {
    ChmodSsh,
    ConfigureIfConfigSsh,
    ConfigureNetworkSsh,
    CreateFileSsh,
    IsAvailable,
    SetupPlanesSsh,
    SshCommand,
    SyncFileSsh,
}

impl Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::ChmodSsh => "chmod_ssh",
            Self::ConfigureIfConfigSsh => "configure_if_config_ssh",
            Self::ConfigureNetworkSsh => "configure_network_ssh",
            Self::CreateFileSsh => "create_file_ssh",
            Self::IsAvailable => "is_available",
            Self::SetupPlanesSsh => "setup_planes_ssh",
            Self::SshCommand => "ssh_command",
            Self::SyncFileSsh => "sync_file_ssh",
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
        ActionName::ChmodSsh => deserialize_input(input).map(Input::ChmodSsh),
        ActionName::CreateFileSsh => deserialize_input(input).map(Input::CreateFileSsh),
        ActionName::IsAvailable => deserialize_input(input).map(Input::IsAvailable),
        ActionName::ConfigureIfConfigSsh => {
            deserialize_input(input).map(Input::ConfigureIfConfigSsh)
        }
        ActionName::ConfigureNetworkSsh => deserialize_input(input).map(Input::ConfigureNetworkSsh),
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
    pub(crate) host: String,
    pub(crate) cp_addr: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct SyncFileSsh {
    #[validate(length(min = 1))]
    pub(crate) host: String,
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

/// Wait for a host with the given `fqdn` to appear in the EMF database
/// until `timeout`.
///
/// If timeout is not defined, it defaults to 30 seconds.
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct IsAvailable {
    pub(crate) fqdn: String,
    #[serde(with = "humantime_serde")]
    #[serde(default)]
    pub(crate) timeout: Option<Duration>,
}

/// Configure the interfaces on a given host machine. `nics` provides a map
/// of network nics to their corresponding config. This config will be used
/// to configure its interface on the host under /etc/sysconfig/network-scripts.
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct ConfigureIfConfigSsh {
    #[validate(length(min = 1))]
    pub(crate) host: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
    #[validate(length(min = 1))]
    pub(crate) nic: String,
    #[validate(length(min = 1))]
    pub(crate) device: String,
    #[serde(default)]
    pub(crate) cfg: Option<String>,
    #[serde(default)]
    pub(crate) master: Option<String>,
    #[validate(length(min = 1))]
    pub(crate) ip: String,
    #[validate(length(min = 1))]
    pub(crate) netmask: String,
    #[serde(default)]
    pub(crate) gateway: Option<String>,
}

/// Change the permissions of a file on the host.
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct ChmodSsh {
    #[validate(length(min = 1))]
    pub(crate) host: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
    #[validate(length(min = 1))]
    pub(crate) file_path: String,
    #[validate(length(min = 1))]
    pub(crate) permissions: String,
}

/// Tune's `/etc/sysconfig/network`
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct ConfigureNetworkSsh {
    #[validate(length(min = 1))]
    pub(crate) host: String,
    #[serde(default)]
    pub(crate) ssh_opts: SshOpts,
    #[validate(length(min = 1))]
    pub(crate) hostname: String,
    #[serde(default)]
    pub(crate) gateway_device: Option<String>,
}
