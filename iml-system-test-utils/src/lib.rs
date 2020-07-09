pub mod snapshots;
pub mod ssh;
pub mod vagrant;

use async_trait::async_trait;
use futures::future::try_join_all;
use iml_cmd::{CheckedCommandExt, CmdError};
use iml_wire_types::Branding;
use ssh::create_iml_diagnostics;
use std::{collections::HashMap, env, io, str, time::Duration};
use tokio::{
    fs::{canonicalize, File},
    io::AsyncWriteExt,
    process::Command,
    time::delay_for,
};

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
    async fn handle_test_result(self, hosts: Vec<&str>, prefix: &str) -> Result<Config, CmdError>;
}

#[async_trait]
impl<T: Into<CmdError> + Send> WithSos for Result<Config, T> {
    async fn handle_test_result(self, hosts: Vec<&str>, prefix: &str) -> Result<Config, CmdError> {
        create_iml_diagnostics(hosts, prefix).await?;

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
        let all_hosts = vec![self.iscsi, self.manager];

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
    pub fn manager_and_storage_server_ips(&self) -> Vec<&'static str> {
        [&[self.manager_ip][..], &self.mds_ips[..], &self.oss_ips[..]].concat()
    }
    pub fn manager_and_storage_server_and_client_ips(&self) -> Vec<&'static str> {
        [
            &[self.manager_ip][..],
            &self.mds_ips[..],
            &self.oss_ips[..],
            &self.client_ips[..],
        ]
        .concat()
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

pub async fn wait_for_ntp(config: &Config) -> Result<(), CmdError> {
    ssh::wait_for_ntp(config.storage_server_ips()).await?;

    Ok(())
}

pub async fn wait_on_services_ready(config: &Config) -> Result<(), CmdError> {
    if config.test_type == TestType::Rpm {
        let (_, output) =
            ssh::ssh_exec(config.manager_ip, "systemctl list-dependencies iml-manager.target | tail -n +2 | awk '{print$2}' | awk '{print substr($1, 3)}' | grep -v iml-settings-populator.service | grep -v iml-sfa.service").await?;

        let status_commands = str::from_utf8(&output.stdout)
            .expect("Couldn't parse service list")
            .lines()
            .map(|s| {
                tracing::debug!("checking status of service {}", s);

                async move {
                    let mut cmd = ssh::systemd_status(config.manager_ip, s).await?;
                    try_command_n_times(50, 5, &mut cmd).await?;

                    Ok::<(), CmdError>(())
                }
            });

        try_join_all(status_commands).await?;
    } else {
        let mut cmd = ssh::systemd_status(config.manager_ip, "iml-docker.service").await?;
        try_command_n_times(50, 5, &mut cmd).await?;
    }

    Ok(())
}

pub async fn setup_bare(config: Config) -> Result<Config, CmdError> {
    vagrant::up()
        .await?
        .arg(config.manager)
        .checked_status()
        .await?;

    if config.test_type == TestType::Rpm {
        match env::var("REPO_URI") {
            Ok(x) => {
                vagrant::provision_node(config.manager, "install-iml-repouri")
                    .await?
                    .env("REPO_URI", x)
                    .checked_status()
                    .await?;
            }
            _ => {
                vagrant::provision_node(config.manager, "install-iml-local")
                    .await?
                    .checked_status()
                    .await?;
            }
        };
    } else {
        match env::var("REPO_URI") {
            Ok(x) => {
                vagrant::provision_node(config.manager, "install-iml-docker-repouri")
                    .await?
                    .env("REPO_URI", x)
                    .checked_status()
                    .await?;
            }
            _ => {
                vagrant::provision_node(config.manager, "install-iml-docker-local")
                    .await?
                    .checked_status()
                    .await?;
            }
        };
    }

    vagrant::up()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    match config.ntp_server {
        NtpServer::HostOnly => {
            ssh::configure_ntp_for_host_only_if(config.storage_server_ips()).await?
        }
        NtpServer::Adm => ssh::configure_ntp_for_adm(config.storage_server_ips()).await?,
    };

    vagrant::halt()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    for x in config.all_hosts() {
        vagrant::snapshot_save(
            x,
            snapshots::get_snapshot_name_for_state(&config, TestState::Bare)
                .to_string()
                .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    Ok(config)
}

pub async fn configure_iml(config: Config) -> Result<Config, CmdError> {
    vagrant::up()
        .await?
        .args(&vec![config.manager][..])
        .checked_status()
        .await?;

    if config.test_type == TestType::Rpm {
        configure_rpm_setup(&config).await?;
    } else {
        configure_docker_setup(&config).await?;
    }

    vagrant::halt()
        .await?
        .args(&vec![config.manager][..])
        .checked_status()
        .await?;

    for host in config.all_hosts() {
        vagrant::snapshot_save(
            host,
            snapshots::get_snapshot_name_for_state(&config, TestState::Configured)
                .to_string()
                .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    vagrant::up()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    wait_for_ntp(&config).await?;
    wait_on_services_ready(&config).await?;

    Ok(config)
}

pub async fn deploy_servers(config: Config) -> Result<Config, CmdError> {
    for (profile, hosts) in &config.profile_map {
        let host_ips = config.hosts_to_ips(&hosts);
        for host in host_ips {
            tracing::debug!("pinging host to make sure it is up.");
            ssh::ssh_exec_cmd(host, "uname -r")
                .await?
                .checked_status()
                .await?;
        }

        let hosts: Vec<String> = if config.test_type == TestType::Rpm {
            hosts.iter().map(|x| String::from(*x)).collect()
        } else {
            configure_docker_network(&config).await?;
            get_local_server_names(hosts)
        };

        ssh::add_servers(&config.manager_ip, profile, hosts).await?;
    }

    vagrant::halt()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    for host in config.all_hosts() {
        vagrant::snapshot_save(
            host,
            snapshots::get_snapshot_name_for_state(&config, TestState::ServersDeployed)
                .to_string()
                .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    vagrant::up()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    wait_for_ntp(&config).await?;
    wait_on_services_ready(&config).await?;

    Ok(config)
}

pub async fn configure_docker_network(config: &Config) -> Result<(), CmdError> {
    let host_list = config.profile_map.to_server_list();
    // The configure-docker-network provisioner must be run individually on
    // each server node.
    tracing::debug!(
        "Configuring docker network for the following servers: {:?}",
        host_list
    );
    for host in host_list {
        vagrant::provision_node(host, "configure-docker-network")
            .await?
            .checked_status()
            .await?;
    }

    Ok(())
}

async fn create_monitored_ldiskfs(config: &Config) -> Result<(), CmdError> {
    let xs = config
        .storage_servers()
        .into_iter()
        .map(|x| {
            tracing::debug!("creating ldiskfs fs for {}", x);
            async move {
                vagrant::provision_node(x, "configure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2,mount-ldiskfs-fs,mount-ldiskfs-fs2")
                    .await?
                    .checked_status()
                    .await?;

                Ok::<_, CmdError>(())
            }
        });

    try_join_all(xs).await?;

    Ok(())
}

async fn create_monitored_zfs(config: &Config) -> Result<(), CmdError> {
    let xs = config.storage_servers().into_iter().map(|x| {
        tracing::debug!("creating zfs fs for {}", x);
        async move {
            vagrant::provision_node(
                x,
                "configure-lustre-network,create-pools,zfs-params,create-zfs-fs",
            )
            .await?
            .checked_status()
            .await?;

            Ok::<_, CmdError>(())
        }
    });

    try_join_all(xs).await?;

    Ok(())
}

pub async fn install_fs(config: Config) -> Result<Config, CmdError> {
    match config.fs_type {
        FsType::LDISKFS => ssh::install_ldiskfs_no_iml(&config).await?,
        FsType::ZFS => ssh::install_zfs_no_iml(&config).await?,
    };

    vagrant::halt()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    for x in config.all_hosts() {
        vagrant::snapshot_save(
            x,
            snapshots::get_snapshot_name_for_state(&config, TestState::FsInstalled)
                .to_string()
                .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    vagrant::up()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    wait_for_ntp(&config).await?;
    wait_on_services_ready(&config).await?;

    Ok(config)
}

pub async fn create_fs(config: Config) -> Result<Config, CmdError> {
    match config.fs_type {
        FsType::LDISKFS => create_monitored_ldiskfs(&config).await?,
        FsType::ZFS => create_monitored_zfs(&config).await?,
    };

    wait_for_ntp(&config).await?;
    wait_on_services_ready(&config).await?;

    delay_for(Duration::from_secs(10)).await;

    Ok(config)
}

pub async fn detect_fs(config: Config) -> Result<Config, CmdError> {
    ssh::detect_fs(config.manager_ip).await?;

    Ok(config)
}

pub async fn configure_rpm_setup(config: &Config) -> Result<(), CmdError> {
    let config_content: String = config.get_setup_config();

    let vagrant_path = canonicalize("../vagrant/").await?;
    let mut config_path = vagrant_path.clone();
    config_path.push("local_settings.py");

    let mut file = File::create(config_path).await?;
    file.write_all(config_content.as_bytes()).await?;

    let mut vm_cmd: String = "sudo cp /vagrant/local_settings.py /usr/share/chroma-manager/".into();
    if config.use_stratagem {
        let mut server_profile_path = vagrant_path.clone();
        server_profile_path.push("stratagem-server.profile");

        let mut file = File::create(server_profile_path).await?;
        file.write_all(STRATAGEM_SERVER_PROFILE.as_bytes()).await?;

        let mut client_profile_path = vagrant_path.clone();
        client_profile_path.push("stratagem-client.profile");

        let mut file = File::create(client_profile_path).await?;
        file.write_all(STRATAGEM_CLIENT_PROFILE.as_bytes()).await?;

        vm_cmd = format!(
            "{}{}",
            vm_cmd,
            "&& sudo chroma-config profile register /vagrant/stratagem-server.profile \
        && sudo chroma-config profile register /vagrant/stratagem-client.profile \
        && sudo systemctl restart iml-manager.target"
        );
    }

    vagrant::rsync(config.manager).await?;

    ssh::ssh_exec_cmd(config.manager_ip, vm_cmd.as_str())
        .await?
        .checked_status()
        .await?;

    Ok(())
}

pub async fn configure_docker_setup(config: &Config) -> Result<(), CmdError> {
    let config_content: String = config.get_setup_config();

    let vagrant_path = canonicalize("../vagrant/").await?;
    let mut config_path = vagrant_path.clone();
    config_path.push("config");

    let mut file = File::create(config_path).await?;
    file.write_all(config_content.as_bytes()).await?;

    let mut vm_cmd: String =
        "sudo mkdir -p /etc/iml-docker/setup && sudo cp /vagrant/config /etc/iml-docker/setup/"
            .into();
    if config.use_stratagem {
        let mut server_profile_path = vagrant_path.clone();
        server_profile_path.push("stratagem-server.profile");

        let mut file = File::create(server_profile_path).await?;
        file.write_all(STRATAGEM_SERVER_PROFILE.as_bytes()).await?;

        let mut client_profile_path = vagrant_path.clone();
        client_profile_path.push("stratagem-client.profile");

        let mut file = File::create(client_profile_path).await?;
        file.write_all(STRATAGEM_CLIENT_PROFILE.as_bytes()).await?;

        vm_cmd = format!(
            "{}{}",
            vm_cmd,
            "&& sudo cp /vagrant/stratagem-server.profile /etc/iml-docker/setup/ \
             && sudo cp /vagrant/stratagem-client.profile /etc/iml-docker/setup/"
        );
    }

    vagrant::rsync(config.manager).await?;

    ssh::ssh_exec_cmd(config.manager_ip, vm_cmd.as_str())
        .await?
        .checked_status()
        .await?;

    Ok(())
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
