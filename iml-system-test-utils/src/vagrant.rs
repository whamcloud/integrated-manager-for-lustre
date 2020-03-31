// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{iml, CheckedStatus, try_command_n_times};
use std::{collections::HashMap, io, str, time::Duration};
use tokio::{fs, process::Command, time::delay_for};

pub enum NtpServer {
    HostOnly,
    Adm,
}

pub enum FsType {
    LDISKFS,
    ZFS,
}

async fn vagrant() -> Result<Command, io::Error> {
    let mut x = Command::new("vagrant");

    let path = fs::canonicalize("../vagrant").await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn up<'a>() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("up");

    Ok(x)
}

pub async fn destroy<'a>() -> Result<(), io::Error> {
    let mut x = vagrant().await?;

    x.arg("destroy").arg("-f");

    try_command_n_times(3, &mut x).await
}

pub async fn halt() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;
    x.arg("halt");

    Ok(x)
}

pub async fn reload() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;
    x.arg("reload");

    Ok(x)
}

async fn snapshot() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("snapshot");

    Ok(x)
}

pub async fn snapshot_save(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("save").arg("-f").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_restore(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("restore").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_delete(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("delete").arg("-f").arg(host).arg(name);

    Ok(x)
}

pub async fn provision(name: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("provision").arg("--provision-with").arg(name);

    Ok(x)
}

pub async fn run_vm_command(node: &str, cmd: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("ssh").arg("-c").arg(&cmd).arg(node);

    Ok(x)
}

pub async fn get_snapshots() -> Result<HashMap<String, Vec<String>>, io::Error> {
    let mut x = vagrant().await?;

    let snapshots: std::process::Output = x.arg("snapshot").arg("list").output().await?;

    let (_, snapshot_map) = str::from_utf8(&snapshots.stdout)
        .expect("Couldn't parse snapshot list.")
        .lines()
        .fold(("", HashMap::new()), |(key, mut map), x| {
            if x.find("==>").is_some() {
                let key = &x[4..];
                map.insert(key.to_string(), vec![]);
                (&key, map)
            } else {
                let v = map
                    .get_mut(key)
                    .unwrap_or_else(|| panic!("Couldn't find key {} in snapshot map.", key));
                v.push(x.to_string());
                (&key, map)
            }
        });

    Ok(snapshot_map)
}

pub async fn setup_bare(hosts: &[&str]) -> Result<(), Box<dyn std::error::Error>> {
    up().await?.args(hosts).checked_status().await?;

    provision("yum-update")
        .await?
        .args(hosts)
        .checked_status()
        .await?;

    halt().await?.args(hosts).checked_status().await?;

    for x in hosts {
        snapshot_save(x, "bare").await?.checked_status().await?;
    }

    up().await?.args(hosts).checked_status().await?;

    Ok(())
}

pub async fn setup_iml_install(hosts: &[&str]) -> Result<(), Box<dyn std::error::Error>> {
    setup_bare(hosts).await?;

    provision("install-iml-local")
        .await?
        .args(hosts)
        .checked_status()
        .await?;

    halt().await?.args(hosts).checked_status().await?;

    for host in hosts {
        snapshot_save(host, "iml-installed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?.args(hosts).checked_status().await?;

    Ok(())
}

pub async fn setup_deploy_servers(
    config: &ClusterConfig,
    profile: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    setup_iml_install(&config.all()).await?;

    run_vm_command(
        "adm",
        &format!(
            "iml server add -h {} -p {}",
            config.storage_servers().join(","),
            profile
        ),
    )
    .await?
    .checked_status()
    .await?;

    halt().await?.args(config.all()).checked_status().await?;

    for host in config.all() {
        snapshot_save(host, "iml-deployed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?.args(config.all()).checked_status().await?;

    Ok(())
}

pub async fn setup_deploy_docker_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    server_map: HashMap<String, &[String], S>,
) -> Result<(), Box<dyn std::error::Error>> {
    setup_bare(&config.iscsi_and_storage_servers()).await?;

    let storage_servers: Vec<&str> = config.storage_servers();
    for host in &storage_servers {
        configure_docker_network(host).await?;
    }

    delay_for(Duration::from_secs(3)).await;
    iml::server_add(&server_map).await?;

    halt().await?.args(config.all()).checked_status().await?;

    for host in config.all() {
        snapshot_save(host, "servers-deployed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?
        .args(&config.iscsi_and_storage_servers())
        .checked_status()
        .await?;

    Ok(())
}

pub async fn configure_docker_network(host: &str) -> Result<(), io::Error> {
    provision("configure-docker-network")
        .await?
        .arg(host)
        .checked_status()
        .await?;

    Ok(())
}

pub async fn configure_ntp(config: &ClusterConfig, ntp_server: NtpServer) -> Result<(), io::Error> {
    match ntp_server {
        NtpServer::HostOnly => {
            provision("configure-ntp-docker")
                .await?
                .args(&config.storage_servers())
                .checked_status()
                .await?
        }
        NtpServer::Adm => {
            provision("configure-ntp")
                .await?
                .args(&config.storage_servers())
                .checked_status()
                .await?
        }
    };

    Ok(())
}

pub async fn configure_ntp_for_host_only_if(config: &ClusterConfig) -> Result<(), io::Error> {
    configure_ntp(config, NtpServer::HostOnly).await?;

    Ok(())
}

pub async fn configure_ntp_for_adm(config: &ClusterConfig) -> Result<(), io::Error> {
    configure_ntp(config, NtpServer::Adm).await?;

    Ok(())
}

async fn create_monitored_fs(hosts: &[&str], provision_scripts: &str) -> Result<(), io::Error> {
    provision("wait-for-ntp")
        .await?
        .args(hosts)
        .checked_status()
        .await?;

    provision(provision_scripts).await?.checked_status().await?;

    Ok(())
}

async fn create_monitored_ldiskfs(hosts: &[&str]) -> Result<(), io::Error> {
    create_monitored_fs(&hosts, "install-ldiskfs-no-iml,configure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2,mount-ldiskfs-fs,mount-ldiskfs-fs2").await?;

    Ok(())
}

async fn create_monitored_zfs(hosts: &[&str]) -> Result<(), io::Error> {
    create_monitored_fs(
        &hosts,
        "install-zfs-no-iml,configure-lustre-network,create-pools,zfs-params,create-zfs-fs",
    )
    .await?;

    Ok(())
}

pub async fn create_fs(fs_type: FsType, hosts: &[&str]) -> Result<(), io::Error> {
    match fs_type {
        FsType::LDISKFS => create_monitored_ldiskfs(&hosts).await?,
        FsType::ZFS => create_monitored_zfs(&hosts).await?,
    };

    Ok(())
}

pub struct ClusterConfig {
    manager: &'static str,
    mds: Vec<&'static str>,
    oss: Vec<&'static str>,
    clients: Vec<&'static str>,
    iscsi: &'static str,
}

impl Default for ClusterConfig {
    fn default() -> Self {
        ClusterConfig {
            manager: "adm",
            mds: vec!["mds1", "mds2"],
            oss: vec!["oss1", "oss2"],
            clients: vec!["c1"],
            iscsi: "iscsi",
        }
    }
}

impl ClusterConfig {
    pub fn all(&self) -> Vec<&str> {
        let mut xs = vec![self.iscsi, self.manager];

        xs.extend(self.storage_servers());
        xs.extend(&self.clients);

        xs
    }
    pub fn storage_servers(&self) -> Vec<&str> {
        [&self.mds[..], &self.oss[..]].concat()
    }
    pub fn iscsi_and_storage_servers(&self) -> Vec<&str> {
        [&[self.iscsi][..], &self.storage_servers()].concat()
    }
    pub fn get_mds_servers(&self) -> Vec<&str> {
        [&self.mds[..]].concat()
    }
    pub fn get_oss_servers(&self) -> Vec<&str> {
        [&self.oss[..]].concat()
    }
    pub fn get_client_servers(&self) -> Vec<&str> {
        [&self.clients[..]].concat()
    }
}
