pub mod docker;
pub mod iml;
pub mod vagrant;

use iml_wire_types::Branding;
use std::{io, time::Duration};
use tokio::{process::Command, time::delay_for};

pub struct SetupConfig {
    pub use_stratagem: bool,
    pub branding: Branding,
}

pub enum SetupConfigType {
    RpmSetup(SetupConfig),
    DockerSetup(SetupConfig),
}

impl From<&SetupConfigType> for String {
    fn from(config: &SetupConfigType) -> Self {
        match config {
            SetupConfigType::RpmSetup(c) => format!(
                r#"USE_STRATAGEM = {}
BRANDING = "{}""#,
                if c.use_stratagem { "True" } else { "False" },
                c.branding.to_string()
            ),
            SetupConfigType::DockerSetup(c) => format!(
                r#"USE_STRATAGEM={}
            BRANDING={}"#,
                c.use_stratagem,
                c.branding.to_string()
            ),
        }
    }
}

impl<'a> From<&'a SetupConfigType> for &'a SetupConfig {
    fn from(config: &'a SetupConfigType) -> Self {
        match config {
            SetupConfigType::RpmSetup(x) => x,
            SetupConfigType::DockerSetup(x) => x,
        }
    }
}

pub const STRATAGEM_SERVER_PROFILE: &str = r#"{
    "ui_name": "Stratagem Policy Engine Server",
    "ui_description": "A server running the Stratagem Policy Engine",
    "managed": false,
    "worker": false,
    "name": "stratagem_server",
    "initial_state": "monitored",
    "ntp": false,
    "corosync": false,
    "corosync2": false,
    "pacemaker": false,
    "repolist": [
      "base"
    ],
    "packages": [],
    "validation": [
      {
        "description": "A server running the Stratagem Policy Engine",
        "test": "distro_version < 8 and distro_version >= 7"
      }
    ]
  }
  "#;

pub const STRATAGEM_CLIENT_PROFILE: &str = r#"{
    "ui_name": "Stratagem Client Node",
    "managed": true,
    "worker": true,
    "name": "stratagem_client",
    "initial_state": "managed",
    "ntp": true,
    "corosync": false,
    "corosync2": false,
    "pacemaker": false,
    "ui_description": "A client that can receive stratagem data",
    "packages": [
      "python2-iml-agent-management",
      "lustre-client"
    ],
    "repolist": [
      "base",
      "lustre-client"
    ]
  }
  "#;

pub async fn try_command_n_times(max_tries: u32, cmd: &mut Command) -> Result<(), io::Error> {
    let mut count = 1;
    let mut r = cmd.status().await?;

    // try to run the command max_tries times until it succeeds. There is a delay of 1 second.
    while !r.success() && count < max_tries {
        println!("Trying command: {:?} - Attempt #{}", cmd, count + 1);
        count += 1;

        delay_for(Duration::from_secs(1)).await;

        r = cmd.status().await?;
    }

    if r.success() {
        Ok(())
    } else {
        Err(io::Error::new(
            io::ErrorKind::Other,
            format!(
                "Command {:?} failed to succeed after {} attempts.",
                cmd, max_tries
            ),
        ))
    }
}

pub fn get_local_server_names<'a>(servers: &'a [&'a str]) -> Vec<String> {
    servers
        .iter()
        .map(move |x| format!("{}.local", x))
        .collect()
}
