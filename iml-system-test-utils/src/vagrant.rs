// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    iml, try_command_n_times, SetupConfig, STRATAGEM_CLIENT_PROFILE, STRATAGEM_SERVER_PROFILE,
};
use iml_cmd::{CheckedCommandExt, CmdError};
use std::{collections::HashMap, io, str, time::Duration};
use tokio::{
    fs::{canonicalize, File},
    io::AsyncWriteExt,
    process::Command,
    time::delay_for,
};

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

    let path = canonicalize("../vagrant/").await?;
    println!("Setting current path for vagrant to {:?}", path);

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

pub async fn provision_node(node: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("provision")
        .arg(node)
        .arg("--provision-with")
        .arg(name);

    Ok(x)
}

pub async fn run_vm_command(node: &str, cmd: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("ssh").arg("-c").arg(&cmd).arg(node);

    Ok(x)
}

pub async fn rsync(host: &str) -> Result<(), CmdError> {
    let mut x = vagrant().await?;

    x.arg("rsync").arg(host).checked_status().await
}

pub async fn setup_bare(
    hosts: &[&str],
    config: &ClusterConfig,
    ntp_server: NtpServer,
) -> Result<(), Box<dyn std::error::Error>> {
    up().await?.args(hosts).checked_status().await?;

    provision("yum-update")
        .await?
        .args(hosts)
        .checked_status()
        .await?;

    match ntp_server {
        NtpServer::HostOnly => configure_ntp_for_host_only_if(&config.storage_servers()).await?,
        NtpServer::Adm => configure_ntp_for_adm(&config.storage_servers()).await?,
    };

    halt().await?.args(hosts).checked_status().await?;

    for x in hosts {
        snapshot_save(x, "bare").await?.checked_status().await?;
    }

    up().await?.args(hosts).checked_status().await?;

    Ok(())
}

pub async fn setup_iml_install(
    hosts: &[&str],
    setup_config: &SetupConfig,
    config: &ClusterConfig,
) -> Result<(), Box<dyn std::error::Error>> {
    up().await?.arg(config.manager).checked_status().await?;
    provision_node(config.manager, "yum-update,install-iml-local")
        .await?
        .checked_status()
        .await?;

    setup_bare(hosts, &config, NtpServer::Adm).await?;

    configure_rpm_setup(setup_config, &config).await?;

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

pub async fn setup_deploy_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    setup_config: &SetupConfig,
    server_map: HashMap<String, &[String], S>,
) -> Result<(), Box<dyn std::error::Error>> {
    setup_iml_install(&config.all(), &setup_config, &config).await?;

    provision("wait-for-ntp")
        .await?
        .args(&config.storage_servers()[..])
        .checked_status()
        .await?;

    for (profile, hosts) in server_map {
        run_vm_command(
            config.manager,
            &format!("iml server add -h {} -p {}", hosts.join(","), profile),
        )
        .await?
        .checked_status()
        .await?;
    }

    halt().await?.args(config.all()).checked_status().await?;

    for host in config.all() {
        snapshot_save(host, "servers-deployed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?.args(config.all()).checked_status().await?;

    provision("wait-for-ntp")
        .await?
        .args(&config.storage_servers()[..])
        .checked_status()
        .await?;

    Ok(())
}

pub async fn add_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    server_map: &HashMap<String, &[String], S>,
) -> Result<(), CmdError> {
    iml::server_add(&server_map).await?;

    halt()
        .await?
        .args(config.iscsi_and_storage_servers())
        .checked_status()
        .await?;

    for host in config.iscsi_and_storage_servers() {
        snapshot_save(host, "servers-deployed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?
        .args(&config.iscsi_and_storage_servers())
        .checked_status()
        .await
}

pub async fn setup_deploy_docker_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    server_map: HashMap<String, &[String], S>,
) -> Result<(), Box<dyn std::error::Error>> {
    setup_bare(
        &config.iscsi_and_storage_servers(),
        &config,
        NtpServer::HostOnly,
    )
    .await?;

    provision("wait-for-ntp-docker")
        .await?
        .args(&config.storage_servers()[..])
        .checked_status()
        .await?;

    delay_for(Duration::from_secs(30)).await;

    configure_docker_network(&config.storage_servers()[..]).await?;

    add_servers(&config, &server_map).await?;

    provision("wait-for-ntp-docker")
        .await?
        .args(&config.storage_servers()[..])
        .checked_status()
        .await?;

    Ok(())
}

pub async fn configure_docker_network(hosts: &[&str]) -> Result<(), CmdError> {
    // The configure-docker-network provisioner must be run individually on
    // each server node.
    for host in hosts {
        provision_node(host, "configure-docker-network")
            .await?
            .checked_status()
            .await?;
    }

    Ok(())
}

pub async fn configure_ntp(hosts: &[&str], ntp_server: NtpServer) -> Result<(), CmdError> {
    match ntp_server {
        NtpServer::HostOnly => {
            provision("configure-ntp-docker")
                .await?
                .args(hosts)
                .checked_status()
                .await?
        }
        NtpServer::Adm => {
            provision("configure-ntp")
                .await?
                .args(hosts)
                .checked_status()
                .await?
        }
    };

    Ok(())
}

pub async fn configure_ntp_for_host_only_if(hosts: &[&str]) -> Result<(), CmdError> {
    configure_ntp(&hosts, NtpServer::HostOnly).await?;

    Ok(())
}

pub async fn configure_ntp_for_adm(hosts: &[&str]) -> Result<(), CmdError> {
    configure_ntp(&hosts, NtpServer::Adm).await?;

    Ok(())
}

async fn create_monitored_ldiskfs() -> Result<(), CmdError> {
    provision("install-ldiskfs-no-iml,configure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2,mount-ldiskfs-fs,mount-ldiskfs-fs2")
        .await?
        .checked_status()
        .await
}

async fn create_monitored_zfs() -> Result<(), CmdError> {
    provision("install-zfs-no-iml,configure-lustre-network,create-pools,zfs-params,create-zfs-fs")
        .await?
        .checked_status()
        .await
}

pub async fn create_fs(fs_type: FsType) -> Result<(), CmdError> {
    match fs_type {
        FsType::LDISKFS => create_monitored_ldiskfs().await?,
        FsType::ZFS => create_monitored_zfs().await?,
    };

    Ok(())
}

pub async fn configure_rpm_setup(
    setup: &SetupConfig,
    cluster_config: &ClusterConfig,
) -> Result<(), CmdError> {
    let config = format!(
        r#"USE_STRATAGEM={}
BRANDING={}"#,
        setup.use_stratagem,
        setup.branding.to_string()
    );

    let vagrant_path = canonicalize("../vagrant/").await?;
    let mut config_path = vagrant_path.clone();
    config_path.push("local_settings.py");

    let mut file = File::create(config_path).await?;
    file.write_all(config.as_bytes()).await?;

    if setup.use_stratagem {
        let mut server_profile_path = vagrant_path.clone();
        server_profile_path.push("stratagem-server.profile");

        let mut file = File::create(server_profile_path).await?;
        file.write_all(STRATAGEM_SERVER_PROFILE.as_bytes()).await?;

        let mut client_profile_path = vagrant_path.clone();
        client_profile_path.push("stratagem-client.profile");

        let mut file = File::create(client_profile_path).await?;
        file.write_all(STRATAGEM_CLIENT_PROFILE.as_bytes()).await?;
    }

    rsync(cluster_config.manager).await?;

    run_vm_command(
        cluster_config.manager,
        "cp /vagrant/local_settings.py /usr/share/chroma-manager/ \
            && chroma-config profile register /vagrant/stratagem-server.profile \
            && chroma-config profile register /vagrant/stratagem-client.profile \
            && systemctl restart iml-manager.target",
    )
    .await?
    .checked_status()
    .await?;

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
