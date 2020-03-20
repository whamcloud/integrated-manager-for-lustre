// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{iml, CheckedStatus};
use std::{collections::HashMap, io, str, thread, time};
use tokio::{fs, process::Command};

pub enum NtpServer {
    HostOnly,
    Adm,
}

async fn vagrant() -> Result<Command, io::Error> {
    let mut x = Command::new("vagrant");

    let path = fs::canonicalize("../vagrant").await?;

    x.current_dir(path);

    Ok(x)
}

async fn ssh() -> Result<Command, io::Error> {
    let mut x = Command::new("ssh");

    let path = fs::canonicalize("../vagrant").await?;
    let mut private_key = path.clone();
    private_key.push("id_rsa");

    x.current_dir(&path).arg("-i").arg(private_key);

    Ok(x)
}

pub async fn up<'a>() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("up").arg("--provision");

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

pub async fn reload() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;
    x.arg("reload").arg("--provision");

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

    x.arg("ssh").arg("-c").arg(&format!("{}", cmd)).arg(node);

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
                    .expect(format!("Couldn't find key {} in snapshot map.", key).as_str());
                v.push(x.to_string());
                (&key, map)
            }
        });

    Ok(snapshot_map)
}

pub async fn setup_bare(hosts: &[&str]) -> Result<(), Box<dyn std::error::Error>> {
    println!("snapshots doesn't contain bare");
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
    let storage_servers: Vec<&str> = config.storage_servers();

    setup_bare(&config.iscsi_and_storage_servers()).await?;

    for host in &storage_servers {
        configure_docker_network(host).await?;
    }

    let server_names: Vec<String> = storage_servers
        .iter()
        .map(move |x| format!("{}.local", x))
        .collect();
    let server_names: Vec<&str> = server_names.iter().map(|x| &**x).collect();

    iml::server_add(&server_names[..], profile).await?;

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

pub async fn create_monitored_ldiskfs(config: &ClusterConfig) -> Result<(), io::Error> {
    let hosts: &[&str] = &config.storage_servers()[..];

    provision("wait-for-ntp")
        .await?
        .args(hosts)
        .checked_status()
        .await?;
    provision("install-ldiskfs-no-imlconfigure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2,mount-ldiskfs-fs,mount-ldiskfs-fs2").await?.checked_status().await?;

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
    fn iscsi_and_storage_servers(&self) -> Vec<&str> {
        [&[self.iscsi][..], &self.storage_servers()].concat()
    }
}
