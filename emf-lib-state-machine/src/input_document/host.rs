// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::{
    input_document::{deserialize_input, SshOpts, Step, StepPair},
    state_schema,
};
use emf_wire_types::ComponentType;
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
pub enum State {
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

impl From<Input> for state_schema::Input {
    fn from(input: Input) -> Self {
        Self::Host(input)
    }
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

impl From<ActionName> for state_schema::ActionName {
    fn from(name: ActionName) -> Self {
        Self::Host(name)
    }
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

pub fn get_input<'de, D>(action: ActionName, input: D) -> Result<Input, D::Error>
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
    pub host: String,
    pub run: String,
    #[serde(default)]
    pub ssh_opts: SshOpts,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct SetupPlanesSsh {
    #[validate(length(min = 1))]
    pub host: String,
    pub cp_addr: String,
    #[serde(default)]
    pub ssh_opts: SshOpts,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct SyncFileSsh {
    #[validate(length(min = 1))]
    pub host: String,
    pub from: String,
    #[serde(default)]
    pub ssh_opts: SshOpts,
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct CreateFileSsh {
    pub host: String,
    pub contents: String,
    pub path: String,
    #[serde(default)]
    pub ssh_opts: SshOpts,
}

/// Wait for a host with the given `fqdn` to appear in the EMF database
/// until `timeout`.
///
/// If timeout is not defined, it defaults to 30 seconds.
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct IsAvailable {
    pub host: String,
    #[serde(with = "humantime_serde")]
    #[serde(default)]
    pub timeout: Option<Duration>,
    #[serde(default)]
    pub ssh_opts: SshOpts,
}

/// Configure the interfaces on a given host machine. `nics` provides a map
/// of network nics to their corresponding config. This config will be used
/// to configure its interface on the host under /etc/sysconfig/network-scripts.
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct ConfigureIfConfigSsh {
    #[validate(length(min = 1))]
    pub host: String,
    #[serde(default)]
    pub ssh_opts: SshOpts,
    #[validate(length(min = 1))]
    pub nic: String,
    #[validate(length(min = 1))]
    pub device: String,
    #[serde(default)]
    pub cfg: Option<String>,
    #[serde(default)]
    pub master: Option<String>,
    #[validate(length(min = 1))]
    pub ip: String,
    #[validate(length(min = 1))]
    pub netmask: String,
    #[serde(default)]
    pub gateway: Option<String>,
}

/// Change the permissions of a file on the host.
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct ChmodSsh {
    #[validate(length(min = 1))]
    pub host: String,
    #[serde(default)]
    pub ssh_opts: SshOpts,
    #[validate(length(min = 1))]
    pub file_path: String,
    #[validate(length(min = 1))]
    pub permissions: String,
}

/// Tune's `/etc/sysconfig/network`
#[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
#[serde(deny_unknown_fields)]
pub struct ConfigureNetworkSsh {
    #[validate(length(min = 1))]
    pub host: String,
    #[serde(default)]
    pub ssh_opts: SshOpts,
    #[validate(length(min = 1))]
    pub hostname: String,
    #[serde(default)]
    pub gateway_device: Option<String>,
}

pub fn reset_machine_id_step(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::SshCommand.into()),
        id: format!("Reset machine-id on {}", &host),
        inputs: Input::SshCommand(SshCommand {
            host,
            run: r#": > /etc/machine-id
                              systemd-machine-id-setup"#
                .to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn sync_dataplane_token(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::SyncFileSsh.into()),
        id: format!("Sync dataplane token on {}", &host),
        inputs: Input::SyncFileSsh(SyncFileSsh {
            host,
            from: "/etc/emf/tokens/dataplane-token".to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn setup_planes(host: String, ssh_opts: SshOpts) -> Step {
    let cp_addr = emf_manager_env::get_cp_addr();

    Step {
        action: StepPair::new(ComponentType::Host, ActionName::SetupPlanesSsh.into()),
        id: format!("Setup Control plane and dataplane on {}", &host),
        inputs: Input::SetupPlanesSsh(SetupPlanesSsh {
            host,
            cp_addr,
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn add_emf_rpm_repo_step(host: String, ssh_opts: SshOpts) -> Step {
    let port = emf_manager_env::get_port("NGINX_GATEWAY_UNSECURE_PORT");
    let manager_fqdn = emf_manager_env::get_manager_fqdn();

    Step {
        action: StepPair::new(ComponentType::Host, ActionName::CreateFileSsh.into()),
        id: format!("Add emf repo to {}", &host),
        inputs: Input::CreateFileSsh(CreateFileSsh {
            host,
            contents: format!(
                r#"[emf]
name=emf repo
baseurl=http://{}:{}/repo/emf_repo/
gpgcheck=0"#,
                &manager_fqdn, port
            ),
            path: "/etc/yum.repos.d/emf.repo".to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn add_emf_deb_repo_step(host: String, ssh_opts: SshOpts) -> Step {
    let manager_fqdn = emf_manager_env::get_manager_fqdn();

    let port = emf_manager_env::get_port("NGINX_GATEWAY_UNSECURE_PORT");

    Step {
        action: StepPair::new(ComponentType::Host, ActionName::CreateFileSsh.into()),
        id: format!("Add emf deb repo to {}", &host),
        inputs: Input::CreateFileSsh(CreateFileSsh {
            host,
            contents: format!(
                "deb [trusted=yes] http://{}:{}/apt-repo/ emf non-free",
                &manager_fqdn, port
            ),
            path: "/etc/apt/sources.list.d/emf.list".to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn create_cli_conf(host: String, ssh_opts: SshOpts) -> Step {
    let manager_fqdn = emf_manager_env::get_manager_fqdn();
    let port = emf_manager_env::get_port("NGINX_GATEWAY_PORT");

    Step {
        action: StepPair::new(ComponentType::Host, ActionName::CreateFileSsh.into()),
        id: format!("Add CLI config to {}", &host),
        inputs: Input::CreateFileSsh(CreateFileSsh {
            host,
            contents: format!("SERVER_HTTP_URL=https://{}:{}", manager_fqdn, port),
            path: "/etc/emf/cli.conf".to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn install_agent_rpms(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(
            ComponentType::Host,
            ActionName::SshCommand.into(),
        ),
        id: format!("Install emf agent on {}", &host),
        inputs: Input::SshCommand(SshCommand {
            host,
            run: "yum install -y rust-emf-agent rust-emf-cli rust-emf-cli-bash-completion emf-sos-plugin"
                .to_string(),
            ssh_opts,
        }).into(),
        outputs: None,
    }
}

pub fn install_agent_client_rpms(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::SshCommand.into()),
        id: format!("Install emf agent on {}", &host),
        inputs: Input::SshCommand(SshCommand {
            host,
            run: r#"yum install -y \
rust-emf-action-agent \
rust-emf-device-agent \
rust-emf-journal-agent \
rust-emf-network-agent \
rust-emf-host-agent \
rust-emf-ntp-agent \
rust-emf-stats-agent"#
                .to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn install_agent_debs(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::SshCommand.into()),
        id: format!("Install emf agent on {}", &host),
        inputs: Input::SshCommand(SshCommand {
            host,
            run: r#"apt update
apt install -y \
emf-action-agent \
emf-device-agent \
emf-journal-agent \
emf-network-agent \
emf-host-agent \
emf-ntp-agent \
emf-stats-agent"#
                .to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn enable_emf_client_agent(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::SshCommand.into()),
        id: format!("Start agent on {}", &host),
        inputs: Input::SshCommand(SshCommand {
            host,
            run: r#"systemctl enable --now \
emf-action-agent \
emf-device-agent \
emf-journal-agent \
emf-network-agent \
emf-host-agent \
emf-ntp-agent \
emf-stats-agent \
emf-agent.target"#
                .to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn enable_emf_server_agent(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::SshCommand.into()),
        id: format!("Start agent on {}", &host),
        inputs: Input::SshCommand(SshCommand {
            host,
            run: "systemctl enable --now emf-agent.target".to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn wait_for_host_availability(host: String, ssh_opts: SshOpts) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::IsAvailable.into()),
        id: format!("Wait for {} agent to report in", &host),
        inputs: Input::IsAvailable(IsAvailable {
            host,
            timeout: None,
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}

pub fn configure_bonding(
    host: String,
    ssh_opts: SshOpts,
    nic: String,
    bonding_mode: String,
) -> Step {
    Step {
        action: StepPair::new(ComponentType::Host, ActionName::CreateFileSsh.into()),
        id: format!("Configure network bonding on {}", &host),
        inputs: Input::CreateFileSsh(CreateFileSsh {
            host,
            contents: format!(
                r#"
alias {} bonding
options bonding miimon=100 mode={}
"#,
                nic, bonding_mode
            ),
            path: "/etc/modprobe.d/bonding.conf".to_string(),
            ssh_opts,
        })
        .into(),
        outputs: None,
    }
}
