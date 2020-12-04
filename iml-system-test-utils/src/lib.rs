// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod snapshots;
pub mod ssh;
pub mod vagrant;

use async_trait::async_trait;
use futures::future::try_join_all;
use iml_cmd::{CheckedChildExt, CheckedCommandExt};
use iml_graphql_queries::task;
use iml_wire_types::{task::KeyValue, task::TaskArgs, Branding, FsType};
use ssh::create_iml_diagnostics;
use std::{collections::HashMap, env, path::PathBuf, process::Stdio, str, time::Duration};
use tokio::{
    fs::{canonicalize, File},
    io::AsyncWriteExt,
    process::Command,
    time::delay_for,
};

#[derive(Debug, thiserror::Error)]
pub enum TestError {
    #[error(transparent)]
    CmdError(#[from] iml_cmd::CmdError),
    #[error("ASSERT FAILED: {0}")]
    Assert(String),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
}

impl From<std::io::Error> for TestError {
    fn from(err: std::io::Error) -> Self {
        TestError::CmdError(iml_cmd::CmdError::Io(err))
    }
}

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

pub enum TestState {
    Bare,
    LustreRpmsInstalled,
    Configured,
    ServersDeployed,
    FsCreated,
}

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

pub const BASE_CLIENT_PROFILE: &str = r#"{
    "ui_name": "Client Node",
    "managed": false,
    "worker": false,
    "name": "base_client",
    "initial_state": "monitored",
    "ntp": false,
    "corosync": false,
    "corosync2": false,
    "pacemaker": false,
    "ui_description": "A Lustre client",
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
) -> Result<(), TestError> {
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
        Err(TestError::Assert(format!(
            "Command {:?} failed to succeed after {} attempts.",
            cmd, max_tries
        )))
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
    async fn handle_test_result(self, hosts: Vec<&str>, prefix: &str) -> Result<Config, TestError>;
}

#[async_trait]
impl<T: Into<TestError> + Send> WithSos for Result<Config, T> {
    async fn handle_test_result(self, hosts: Vec<&str>, prefix: &str) -> Result<Config, TestError> {
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
            client: vec!["client1"],
            client_ips: vec!["10.73.10.31"],
            iscsi: "iscsi",
            lustre_version: "2.12.4",
            server_map: vec![
                ("adm", "10.73.10.10"),
                ("mds1", "10.73.10.11"),
                ("mds2", "10.73.10.12"),
                ("oss1", "10.73.10.21"),
                ("oss2", "10.73.10.22"),
                ("client1", "10.73.10.31"),
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
            fs_type: FsType::Ldiskfs,
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
                r#"USE_STRATAGEM={}
BRANDING={}
LOG_LEVEL=10
RUST_LOG=debug
NTP_SERVER_HOSTNAME=adm.local
"#,
                if self.use_stratagem { "True" } else { "False" },
                self.branding.to_string()
            ),
            TestType::Docker => format!(
                r#"USE_STRATAGEM={}
BRANDING={}
LOG_LEVEL=10
RUST_LOG=debug
NTP_SERVER_HOSTNAME=10.73.10.1
"#,
                self.use_stratagem,
                self.branding.to_string()
            ),
        }
    }
}

pub async fn wait_for_ntp(config: &Config) -> Result<(), TestError> {
    match config.test_type {
        TestType::Rpm => ssh::wait_for_ntp_for_adm(&config.storage_server_ips()).await?,
        TestType::Docker => {
            ssh::wait_for_ntp_for_host_only_if(&config.storage_server_ips()).await?
        }
    };

    Ok(())
}

pub async fn wait_on_services_ready(config: &Config) -> Result<(), TestError> {
    match config.test_type {
        TestType::Rpm => {
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

                        Ok::<(), TestError>(())
                    }
                });

            try_join_all(status_commands).await?;
        }
        TestType::Docker => {
            let mut cmd = ssh::systemd_status(config.manager_ip, "iml-docker.service").await?;
            try_command_n_times(50, 5, &mut cmd).await?;
        }
    };

    Ok(())
}

pub async fn setup_bare(config: Config) -> Result<Config, TestError> {
    vagrant::up()
        .await?
        .arg(config.manager)
        .checked_status()
        .await?;

    match config.test_type {
        TestType::Rpm => match env::var("REPO_URI") {
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
        },
        TestType::Docker => {
            configure_docker_network(&[config.manager]).await?;
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
            }
        }
    };

    vagrant::up()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    match config.ntp_server {
        NtpServer::HostOnly => {
            ssh::configure_ntp_for_host_only_if(&config.storage_server_ips()).await?
        }
        NtpServer::Adm => ssh::configure_ntp_for_adm(&config.storage_server_ips()).await?,
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

pub async fn configure_iml(config: Config) -> Result<Config, TestError> {
    vagrant::up()
        .await?
        .args(&vec![config.manager][..])
        .checked_status()
        .await?;

    match config.test_type {
        TestType::Rpm => configure_rpm_setup(&config).await?,
        TestType::Docker => configure_docker_setup(&config).await?,
    };

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

pub async fn deploy_servers(config: Config) -> Result<Config, TestError> {
    for (profile, hosts) in &config.profile_map {
        let host_ips = config.hosts_to_ips(&hosts);
        for host in &host_ips {
            tracing::debug!("pinging host to make sure it is up.");
            ssh::ssh_exec_cmd(host, "uname -r")
                .await?
                .checked_status()
                .await?;
        }

        let hosts: Vec<String> = match config.test_type {
            TestType::Rpm => hosts.iter().map(|x| String::from(*x)).collect(),
            TestType::Docker => {
                configure_docker_network(&config.profile_map.to_server_list()).await?;
                get_local_server_names(hosts)
            }
        };

        ssh::add_servers(&config.manager_ip, profile, hosts).await?;
        ssh::enable_debug_on_hosts(&host_ips).await?;
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

pub async fn configure_docker_network(host_list: &[&str]) -> Result<(), TestError> {
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

async fn create_monitored_ldiskfs(config: &Config) -> Result<(), TestError> {
    let xs = config.storage_servers().into_iter().map(|x| {
        tracing::debug!("creating ldiskfs fs for {}", x);
        async move {
            vagrant::provision_node(
                x,
                "configure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2",
            )
            .await?
            .checked_status()
            .await?;

            Ok::<_, TestError>(())
        }
    });

    try_join_all(xs).await?;

    Ok(())
}

async fn create_monitored_zfs(config: &Config) -> Result<(), TestError> {
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

            Ok::<_, TestError>(())
        }
    });

    try_join_all(xs).await?;

    Ok(())
}

pub async fn install_fs(config: Config) -> Result<Config, TestError> {
    vagrant::up()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    ssh::install_ldiskfs_zfs_no_iml(&config).await?;

    vagrant::halt()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    for x in config.all_hosts() {
        vagrant::snapshot_save(
            x,
            snapshots::get_snapshot_name_for_state(&config, TestState::LustreRpmsInstalled)
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

pub async fn create_fs(config: Config) -> Result<Config, TestError> {
    match config.fs_type {
        FsType::Ldiskfs => create_monitored_ldiskfs(&config).await?,
        FsType::Zfs => create_monitored_zfs(&config).await?,
    };

    wait_for_ntp(&config).await?;
    wait_on_services_ready(&config).await?;

    delay_for(Duration::from_secs(10)).await;

    Ok(config)
}

async fn mount_fs(config: &Config) -> Result<usize, TestError> {
    let (count, provisioner) = match config.fs_type {
        FsType::Ldiskfs => (2, "mount-ldiskfs-fs,mount-ldiskfs-fs2"),
        FsType::Zfs => (1, "mount-zfs-fs"),
    };

    let xs = config.storage_servers().into_iter().map(|x| {
        tracing::debug!("mount fs for {}", x);
        async move {
            vagrant::provision_node(x, provisioner)
                .await?
                .checked_status()
                .await?;

            Ok::<_, TestError>(())
        }
    });

    try_join_all(xs).await?;

    Ok(count)
}

pub async fn detect_fs(config: Config) -> Result<Config, TestError> {
    let count = mount_fs(&config).await?;
    ssh::detect_fs(config.manager_ip).await?;

    let fs_info = ssh::list_fs_json(config.manager_ip).await?;

    if fs_info.len() == count {
        Ok(config)
    } else {
        tracing::error!(
            "Failed to detect correct number of FS expected: {}, actual: {}, INFO {:?}",
            count,
            fs_info.len(),
            &fs_info
        );
        Err(TestError::Assert(format!(
            "Failed to detect the expected number of filesystems (expected: {}, actual: {})",
            count,
            fs_info.len(),
        )))
    }
}

pub async fn mount_clients(config: Config) -> Result<Config, TestError> {
    let xs = config.client_servers().into_iter().map(|x| {
        tracing::debug!("provisioning client {}", x);
        async move {
            vagrant::provision_node(
                x,
                "install-lustre-client,configure-lustre-client-network,mount-lustre-client",
            )
            .await?
            .checked_status()
            .await?;

            Ok::<_, TestError>(())
        }
    });

    try_join_all(xs).await?;

    Ok(config)
}

pub async fn test_stratagem_taskqueue(config: Config) -> Result<Config, TestError> {
    // create file
    let (_, output) = ssh::ssh_exec(
        config.client_server_ips()[0],
        "touch /mnt/fs/reportfile; lfs path2fid /mnt/fs/reportfile",
    )
    .await?;

    // Create Task
    let q = task::create::build(
        "fs",
        TaskArgs {
            name: "testfile".into(),
            single_runner: true,
            keep_failed: false,
            actions: vec!["stratagem.warning".into()],
            pairs: vec![KeyValue {
                key: "report_name".into(),
                value: "test-taskfile.txt".into(),
            }],
            needs_cleanup: false,
        },
    );

    ssh::graphql_call::<_, iml_graphql_queries::Response<task::create::Resp>>(&config, &q).await?;

    // TODO wait for command to complete
    delay_for(Duration::from_secs(20)).await;

    // send fid
    let cmd = r#"socat - unix-connect:/run/iml/postman-testfile.sock"#;
    let fid = format!(
        "{{ \"fid\": \"{}\" }}",
        String::from_utf8(output.stdout).unwrap().trim()
    );

    let mut ssh_child = ssh::ssh_exec_cmd(config.mds_ips[0], &cmd)
        .await?
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .spawn()?;

    let ssh_stdin = ssh_child.stdin.as_mut().unwrap();
    ssh_stdin.write_all(fid.as_bytes()).await?;
    ssh_child.wait_with_checked_output().await?;

    // TODO wait for fid to process by checking Task
    delay_for(Duration::from_secs(20)).await;

    // check output on manager
    if let Ok((_, output)) = ssh::ssh_exec(
        config.manager_ip,
        "iml debugapi get report/test-taskfile.txt",
    )
    .await
    {
        let x = String::from_utf8_lossy(&output.stdout);
        let x = x.lines().nth(1).unwrap().trim();

        assert_eq!(x, "/mnt/fs/reportfile");

        Ok(config)
    } else {
        Err(TestError::Assert("Report file not found in API.".into()))
    }
}

// Returns list of server profile file names
async fn configure_extra_profile(vagrant_path: &PathBuf) -> Result<Vec<String>, TestError> {
    let mut rc = vec![];

    // Register Stratagem Client Profile
    let mut profile_path = vagrant_path.clone();
    profile_path.push("stratagem-client.profile");
    rc.push("stratagem-client.profile".into());

    let mut file = File::create(&profile_path).await?;
    file.write_all(STRATAGEM_CLIENT_PROFILE.as_bytes()).await?;

    // Register Base Client Profile
    let mut profile_path = vagrant_path.clone();
    profile_path.push("base-client.profile");
    rc.push("base-client.profile".into());

    let mut file = File::create(&profile_path).await?;
    file.write_all(BASE_CLIENT_PROFILE.as_bytes()).await?;

    Ok(rc)
}

pub async fn configure_rpm_setup(config: &Config) -> Result<(), TestError> {
    let config_content: String = config.get_setup_config();

    let vagrant_path = canonicalize("../vagrant/").await?;
    let mut config_path = vagrant_path.clone();
    config_path.push("overrides.conf");

    let mut file = File::create(config_path).await?;
    file.write_all(config_content.as_bytes()).await?;

    let path_list = configure_extra_profile(&vagrant_path).await?;

    let vm_cmd = format!(
        "mkdir -p /var/lib/chroma && sudo cp /vagrant/overrides.conf /var/lib/chroma {} \
         && sudo systemctl restart iml-manager.target",
        path_list
            .into_iter()
            .map(|p| format!(" && sudo chroma-config profile register /vagrant/{}", p))
            .collect::<Vec<String>>()
            .concat()
    );

    vagrant::rsync(config.manager).await?;

    ssh::ssh_exec_cmd(config.manager_ip, vm_cmd.as_str())
        .await?
        .checked_status()
        .await?;

    Ok(())
}

pub async fn configure_docker_setup(config: &Config) -> Result<(), TestError> {
    let config_content: String = config.get_setup_config();

    let vagrant_path = canonicalize("../vagrant/").await?;
    let mut config_path = vagrant_path.clone();
    config_path.push("config");

    let mut file = File::create(config_path).await?;
    file.write_all(config_content.as_bytes()).await?;

    let path_list = configure_extra_profile(&vagrant_path).await?;

    let vm_cmd = format!(
        "sudo mkdir -p /etc/iml-docker/setup && sudo cp /vagrant/config /etc/iml-docker/setup/ {}",
        path_list
            .into_iter()
            .map(|p| format!(" && sudo cp /vagrant/{} /etc/iml-docker/setup/", p))
            .collect::<Vec<String>>()
            .concat()
    );

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
            (
                "base_monitored".into(),
                mds_servers.into_iter().chain(oss_servers).collect(),
            ),
            ("stratagem_client".into(), client_servers),
        ]
        .into_iter()
        .collect::<Vec<(&str, Vec<&str>)>>();

        let servers = xs.to_server_list();

        assert_eq!(servers, vec!["mds1", "mds2", "oss1", "oss2", "client1"]);
    }
}
