pub mod docker;
pub mod iml;
pub mod snapshots;
pub mod ssh;
pub mod vagrant;

use async_trait::async_trait;
use iml_cmd::CmdError;
use iml_systemd::SystemdError;
use iml_wire_types::Branding;
use ssh::create_iml_diagnostics;
use std::{collections::HashMap, io, time::Duration};
use tokio::{process::Command, time::delay_for};

#[derive(PartialEq, Clone)]
pub enum TestType {
    Rpm,
    Docker,
}

#[derive(Clone)]
pub enum NtpServer {
    HostOnly,
    Adm,
}

#[derive(Clone)]
pub enum FsType {
    LDISKFS,
    ZFS,
}

pub enum TestState {
    Bare,
    Configured,
    ServersDeployed,
    FsInstalled,
    FsCreated,
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

pub async fn try_command_n_times(
    max_tries: u32,
    delay: u64,
    cmd: &mut Command,
) -> Result<(), CmdError> {
    let mut count = 1;
    let mut r = cmd.status().await?;

    // try to run the command max_tries times until it succeeds. There is a delay of 1 second.
    while !r.success() && count < max_tries {
        tracing::debug!("Trying command: {:?} - Attempt #{}", cmd, count + 1);
        count += 1;

        delay_for(Duration::from_secs(delay)).await;

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
        )
        .into())
    }
}

pub fn get_local_server_names<'a>(servers: &'a [&'a str]) -> Vec<String> {
    servers
        .iter()
        .map(move |x| format!("{}.local", x))
        .collect()
}

use thiserror::Error;

#[derive(Error, Debug)]
pub enum SystemTestError {
    #[error(transparent)]
    CmdError(#[from] CmdError),
    #[error(transparent)]
    SystemdError(#[from] SystemdError),
}

pub trait ServerList {
    fn to_server_list(&self) -> Vec<&str>;
}

impl ServerList for Vec<(&str, Vec<&str>)> {
    fn to_server_list(&self) -> Vec<&str> {
        let server_set: Vec<&str> = self.iter().flat_map(|(_, x)| x).copied().collect();
        let mut xs: Vec<&str> = server_set.into_iter().collect();
        xs.dedup();

        xs
    }
}

#[async_trait]
pub trait WithSos {
    async fn handle_test_result(
        self,
        hosts: Vec<&str>,
        prefix: &str,
    ) -> Result<(), SystemTestError>;
}

#[async_trait]
impl<T: Into<SystemTestError> + Send> WithSos for Result<(), T> {
    async fn handle_test_result(
        self,
        hosts: Vec<&str>,
        prefix: &str,
    ) -> Result<(), SystemTestError> {
        create_iml_diagnostics(&hosts, prefix).await?;

        self.map_err(|e| e.into())
    }
}

#[derive(Clone)]
pub struct Config {
    pub manager: &'static str,
    pub manager_ip: &'static str,
    pub mds: Vec<&'static str>,
    pub mds_ips: Vec<&'static str>,
    pub oss: Vec<&'static str>,
    pub oss_ips: Vec<&'static str>,
    pub client: Vec<&'static str>,
    pub client_ips: Vec<&'static str>,
    pub iscsi: &'static str,
    pub lustre_version: &'static str,
    pub server_map: HashMap<&'static str, &'static str>,
    pub profile_map: Vec<(&'static str, Vec<&'static str>)>,
    pub use_stratagem: bool,
    pub branding: Branding,
    pub test_type: TestType,
    pub ntp_server: NtpServer,
    pub fs_type: FsType,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            manager: "adm",
            manager_ip: "10.73.10.10",
            mds: vec!["mds1", "mds2"],
            mds_ips: vec!["10.73.10.11", "10.73.10.12"],
            oss: vec!["oss1", "oss2"],
            oss_ips: vec!["10.73.10.21", "10.73.10.22"],
            client: vec!["c1"],
            client_ips: vec!["10.73.10.31"],
            iscsi: "iscsi",
            lustre_version: "2.12.4",
            server_map: vec![
                ("adm", "10.73.10.10"),
                ("mds1", "10.73.10.11"),
                ("mds2", "10.73.10.12"),
                ("oss1", "10.73.10.21"),
                ("oss2", "10.73.10.22"),
                ("c1", "10.73.10.31"),
            ]
            .into_iter()
            .collect::<HashMap<&'static str, &'static str>>(),
            profile_map: vec![]
                .into_iter()
                .collect::<Vec<(&'static str, Vec<&'static str>)>>(),
            use_stratagem: false,
            branding: Branding::default(),
            test_type: TestType::Rpm,
            ntp_server: NtpServer::Adm,
            fs_type: FsType::LDISKFS,
        }
    }
}

impl Config {
    pub fn all_hosts(&self) -> Vec<&str> {
        let storage_and_client_servers = self.profile_map.to_server_list();
        let mut all_hosts = vec![self.iscsi];

        if self.test_type == TestType::Rpm {
            all_hosts.extend(&[self.manager]);
        }

        [&all_hosts[..], &storage_and_client_servers[..]].concat()
    }
    pub fn destroy_list(&self) -> Vec<&str> {
        let mut to_destroy = self.all_hosts();
        to_destroy.reverse();

        to_destroy
    }
    pub fn manager_ip(&self) -> Vec<&'static str> {
        vec![self.manager_ip]
    }
    pub fn storage_servers(&self) -> Vec<&'static str> {
        [&self.mds[..], &self.oss[..]].concat()
    }
    pub fn storage_server_ips(&self) -> Vec<&'static str> {
        [&self.mds_ips[..], &self.oss_ips[..]].concat()
    }
    pub fn mds_servers(&self) -> Vec<&'static str> {
        [&self.mds[..]].concat()
    }
    pub fn oss_servers(&self) -> Vec<&'static str> {
        [&self.oss[..]].concat()
    }
    pub fn client_servers(&self) -> Vec<&'static str> {
        [&self.client[..]].concat()
    }
    pub fn client_server_ips(&self) -> Vec<&'static str> {
        [&self.client_ips[..]].concat()
    }
    pub fn lustre_version(&self) -> &'static str {
        self.lustre_version
    }
    pub fn hosts_to_ips(&self, hosts: &[&str]) -> Vec<&'static str> {
        hosts
            .iter()
            .map(|host| {
                self.server_map
                    .get(host)
                    .unwrap_or_else(|| panic!("Couldn't locate {} in server map.", host))
            })
            .copied()
            .collect()
    }
    pub fn get_setup_config(&self) -> String {
        match &self.test_type {
            TestType::Rpm => format!(
                r#"USE_STRATAGEM = {}
BRANDING = "{}""#,
                if self.use_stratagem { "True" } else { "False" },
                self.branding.to_string()
            ),
            TestType::Docker => format!(
                r#"USE_STRATAGEM={}
            BRANDING={}"#,
                self.use_stratagem,
                self.branding.to_string()
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_to_server_list() {
        let config = Config::default();
        let mds_servers = config.mds_servers();
        let oss_servers = config.oss_servers();
        let client_servers = config.client_servers();

        let xs = vec![
            ("stratagem_server".into(), mds_servers),
            ("base_monitored".into(), oss_servers),
            ("stratagem_client".into(), client_servers),
        ]
        .into_iter()
        .collect::<Vec<(&str, Vec<&str>)>>();

        let servers = xs.to_server_list();

        assert_eq!(servers, vec!["mds1", "mds2", "oss1", "oss2", "c1"]);
    }
}
