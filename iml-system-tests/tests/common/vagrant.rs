// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::common::{iml, CheckedStatus};
use std::{io, thread, time};
use tokio::{fs, process::Command};

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

pub async fn destroy<'a>() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("destroy").arg("-f");

    Ok(x)
}

pub async fn halt() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;
    x.arg("halt");

    Ok(x)
}

async fn snapshot() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("snapshot");

    Ok(x)
}

pub async fn snapshot_save(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("save").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_restore(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("restore").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_delete(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("delete").arg(host).arg(name);

    Ok(x)
}

pub async fn provision(name: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("provision").arg("--provision-with").arg(name);

    Ok(x)
}

pub async fn run_vm_command(node: &str, cmd: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("ssh").arg("-c").arg(&format!("{}", cmd)).arg(node);

    Ok(x)
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

pub async fn setup_deploy_docker_servers(
    config: &ClusterConfig,
    profile: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    setup_bare(&[&config.storage_servers()[..], &[config.iscsi]].concat()).await?;

    iml::server_add(&config.storage_servers()[..], profile)
        .await?
        .checked_status()
        .await?;

    halt().await?.args(config.all()).checked_status().await?;

    for host in config.all() {
        snapshot_save(host, "servers-deployed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?.args(config.all()).checked_status().await?;

    Ok(())
}

async fn check_ntp_status(host: &str) -> Result<bool, io::Error> {
    let x = vagrant()
        .await?
        .arg("ssh")
        .arg("-c")
        .arg("'sudo ntpstat'")
        .arg(host)
        .status()
        .await?;

    Ok(x.success())
}

async fn restart_ntpd(hosts: &[&str]) -> Result<(), io::Error> {
    vagrant()
        .await?
        .arg("ssh")
        .arg("-c")
        .arg("'sudo systemctl restart ntpd.service'")
        .arg(hosts.join(" "))
        .checked_status()
        .await?;

    Ok(())
}

async fn restart_ntpd_on(host: &str) -> Result<(), io::Error> {
    vagrant()
        .await?
        .arg("ssh")
        .arg("-c")
        .arg("'sudo systemctl restart ntpd.service'")
        .arg(host)
        .checked_status()
        .await?;

    Ok(())
}

async fn wait_for_ntp(hosts: &[&str]) -> Result<(), io::Error> {
    for host in hosts {
        let mut x = check_ntp_status(host).await?;

        while !x {
            restart_ntpd_on(host).await?;

            let delay = time::Duration::from_millis(20000);
            thread::sleep(delay);

            x = check_ntp_status(host).await?;
        }
    }

    Ok(())
}

async fn configure_ntp(config: &ClusterConfig, ntp_host: &str) -> Result<(), io::Error> {
    let hosts = &config.storage_servers();

    for host in hosts {
        vagrant()
            .await?
            .arg("ssh")
            .arg("-c")
            .arg("'systemctl disable --now chronyd'")
            .arg(host)
            .checked_status()
            .await?;

        vagrant()
            .await?
            .arg("ssh")
            .arg("-c")
            .arg("'yum install -y ntp'")
            .arg(host)
            .checked_status()
            .await?;

        vagrant()
            .await?
            .arg("ssh")
            .arg("-c")
            .arg(format!(
                "'sed -i -e \"/^server /d; $ a server {} iburst\" /etc/ntp.conf'",
                ntp_host
            ))
            .arg(host)
            .checked_status()
            .await?;

        restart_ntpd_on(host).await?;

        vagrant()
            .await?
            .arg("ssh")
            .arg("-c")
            .arg("'sudo systemctl enable ntpd.service'")
            .arg(host)
            .checked_status()
            .await?;
    }

    wait_for_ntp(hosts).await?;

    Ok(())
}

pub async fn configure_ntp_for_host_only_if(config: &ClusterConfig) -> Result<(), io::Error> {
    configure_ntp(config, "10.73.10.1").await?;

    Ok(())
}

pub async fn configure_ntp_for_adm(config: &ClusterConfig) -> Result<(), io::Error> {
    configure_ntp(config, "adm.local").await?;

    Ok(())
}

pub async fn create_monitored_ldiskfs(config: &ClusterConfig) -> Result<(), io::Error> {
    let hosts = &config.storage_servers()[..];

    provision("install-ldiskfs-no-iml")
        .await?
        .checked_status()
        .await?;

    halt().await?.args(hosts).checked_status().await?;
    up().await?.args(hosts).checked_status().await?;

    restart_ntpd(hosts).await?;
    wait_for_ntp(hosts).await?;
    provision("configure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2,mount-ldiskfs-fs,mount-ldiskfs-fs2").await?.checked_status().await?;

    Ok(())
}

pub async fn create_monitored_zfs() -> Result<(), io::Error> {
    provision("vagrant provision --provision-with=install-zfs-no-iml,configure-lustre-network,create-pools,zfs-params,create-zfs-fs").await?.checked_status().await?;

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
    fn all(&self) -> Vec<&str> {
        let mut xs = vec![self.iscsi, self.manager];

        xs.extend(self.storage_servers());
        xs.extend(&self.clients);

        xs
    }
    fn storage_servers(&self) -> Vec<&str> {
        [&self.mds[..], &self.oss[..]].concat()
    }
}
