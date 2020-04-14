// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    iml, pdsh, server_map_to_server_set, try_command_n_times, SetupConfig, SetupConfigType,
    STRATAGEM_CLIENT_PROFILE, STRATAGEM_SERVER_PROFILE,
};
use iml_cmd::{CheckedCommandExt, CmdError};
use std::{collections::HashMap, str, time::Duration};
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

async fn vagrant() -> Result<Command, CmdError> {
    let mut x = Command::new("vagrant");

    let path = canonicalize("../vagrant/").await?;

    x.current_dir(path);

    Ok(x)
}

async fn vbox_manage() -> Result<Command, CmdError> {
    let mut x = Command::new("vboxmanage");

    let path = canonicalize("../vagrant/").await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn up<'a>() -> Result<Command, CmdError> {
    let mut x = vagrant().await?;

    x.arg("up");

    Ok(x)
}

pub async fn destroy<'a>() -> Result<(), CmdError> {
    let mut x = vagrant().await?;

    x.arg("destroy").arg("-f");

    try_command_n_times(3, &mut x).await
}

pub async fn halt() -> Result<Command, CmdError> {
    let mut x = vagrant().await?;
    x.arg("halt");

    Ok(x)
}

pub async fn reload() -> Result<Command, CmdError> {
    let mut x = vagrant().await?;
    x.arg("reload");

    Ok(x)
}

async fn snapshot() -> Result<Command, CmdError> {
    let mut x = vagrant().await?;

    x.arg("snapshot");

    Ok(x)
}

pub async fn snapshot_save(host: &str, name: &str) -> Result<Command, CmdError> {
    let mut x = snapshot().await?;

    x.arg("save").arg("-f").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_restore(host: &str, name: &str) -> Result<Command, CmdError> {
    let mut x = snapshot().await?;

    x.arg("restore").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_delete(host: &str, name: &str) -> Result<Command, CmdError> {
    let mut x = snapshot().await?;

    x.arg("delete").arg("-f").arg(host).arg(name);

    Ok(x)
}

pub async fn provision(name: &str) -> Result<Command, CmdError> {
    let mut x = vagrant().await?;

    x.arg("provision").arg("--provision-with").arg(name);

    Ok(x)
}

pub async fn provision_node(node: &str, name: &str) -> Result<Command, CmdError> {
    let mut x = vagrant().await?;

    x.arg("provision")
        .arg(node)
        .arg("--provision-with")
        .arg(name);

    Ok(x)
}

pub async fn run_vm_command(node: &str, cmd: &str) -> Result<Command, CmdError> {
    let mut x = vagrant().await?;

    x.arg("ssh").arg("-c").arg(&cmd).arg(node);

    Ok(x)
}

pub async fn rsync(host: &str) -> Result<(), CmdError> {
    let mut x = vagrant().await?;

    x.arg("rsync").arg(host).checked_status().await
}

pub async fn detect_fs(config: &ClusterConfig) -> Result<(), CmdError> {
    run_vm_command(config.manager, "iml filesystem detect")
        .await?
        .checked_status()
        .await
}

pub async fn global_prune() -> Result<(), CmdError> {
    let mut x = vagrant().await?;

    x.arg("global-status").arg("--prune").checked_status().await
}

fn vm_list_from_output(output: &str) -> Vec<String> {
    output
        .lines()
        .filter_map(|s| {
            s.split(" ")
                .last()
                .map(|s| s.replace("{", "").replace("}", ""))
        })
        .collect()
}

pub async fn poweroff_running_vms() -> Result<(), CmdError> {
    let mut x = vbox_manage().await?;

    let out = x.arg("list").arg("runningvms").output().await?;

    let running_vms = str::from_utf8(&out.stdout).expect("Couldn't get output.");

    let vm_list = vm_list_from_output(running_vms);

    println!("Powering off the following vm's: {:?}", vm_list);

    for vm in vm_list {
        let mut y = vbox_manage().await?;

        y.arg("controlvm")
            .arg(vm)
            .arg("poweroff")
            .checked_status()
            .await?;
    }

    Ok(())
}

pub async fn unregister_vms() -> Result<(), CmdError> {
    let mut x = vbox_manage().await?;

    let out = x.arg("list").arg("vms").output().await?;

    let vms = str::from_utf8(&out.stdout).expect("Couldn't get output.");

    let vm_list: Vec<String> = vm_list_from_output(vms);

    println!("Unregistering the following vm's: {:?}", vm_list);

    for vm in vm_list {
        let mut y = vbox_manage().await?;

        y.arg("unregistervm")
            .arg(vm)
            .arg("--delete")
            .checked_status()
            .await?;
    }

    Ok(())
}

pub async fn setup_bare(
    hosts: &[&str],
    config: &ClusterConfig,
    ntp_server: NtpServer,
) -> Result<(), CmdError> {
    up().await?.args(hosts).checked_status().await?;

    pdsh::yum_update(&config.storage_server_ips()).await?;

    match ntp_server {
        NtpServer::HostOnly => {
            pdsh::configure_ntp_for_host_only_if(&config.storage_server_ips()).await?
        }
        NtpServer::Adm => pdsh::configure_ntp_for_adm(&config.storage_server_ips()).await?,
    };

    // halt().await?.args(hosts).checked_status().await?;

    // for x in hosts {
    //     snapshot_save(x, "bare").await?.checked_status().await?;
    // }

    Ok(())
}

pub async fn setup_iml_install(
    hosts: &[&str],
    setup_config: &SetupConfigType,
    config: &ClusterConfig,
) -> Result<(), CmdError> {
    up().await?.arg(config.manager).checked_status().await?;
    provision_node(config.manager, "yum-update,install-iml-local")
        .await?
        .checked_status()
        .await?;

    setup_bare(hosts, &config, NtpServer::Adm).await?;

    // up().await?
    //     .args(&vec![config.manager][..])
    //     .checked_status()
    //     .await?;

    configure_rpm_setup(setup_config, &config).await?;

    // halt()
    //     .await?
    //     .args(&vec![config.manager][..])
    //     .checked_status()
    //     .await?;

    // for host in hosts {
    //     snapshot_save(host, "iml-installed")
    //         .await?
    //         .checked_status()
    //         .await?;
    // }

    // up().await?.args(hosts).checked_status().await?;

    Ok(())
}

pub async fn setup_deploy_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    setup_config: &SetupConfigType,
    server_map: HashMap<String, &[&str], S>,
) -> Result<(), CmdError> {
    setup_iml_install(&config.all(), &setup_config, &config).await?;

    for (profile, hosts) in server_map {
        run_vm_command(
            config.manager,
            &format!("iml server add -h {} -p {}", hosts.join(","), profile),
        )
        .await?
        .checked_status()
        .await?;
    }

    // halt().await?.args(config.all()).checked_status().await?;

    // for host in config.all() {
    //     snapshot_save(host, "servers-deployed")
    //         .await?
    //         .checked_status()
    //         .await?;
    // }

    // up().await?.args(config.all()).checked_status().await?;

    Ok(())
}

pub async fn add_docker_servers<S: std::hash::BuildHasher>(
    _: &ClusterConfig,
    server_map: &HashMap<String, &[&str], S>,
) -> Result<(), CmdError> {
    iml::server_add(&server_map).await

    // halt()
    //     .await?
    //     .args(&config.all_but_adm())
    //     .checked_status()
    //     .await?;

    // for host in config.all_but_adm() {
    //     snapshot_save(host, "servers-deployed")
    //         .await?
    //         .checked_status()
    //         .await?;
    // }

    // up().await?
    //     .args(&config.all_but_adm())
    //     .checked_status()
    //     .await
}

pub async fn setup_deploy_docker_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    server_map: HashMap<String, &[&str], S>,
) -> Result<(), CmdError> {
    let server_list = server_map_to_server_set(&server_map);
    setup_bare(&config.all_but_adm()[..], &config, NtpServer::HostOnly).await?;

    // up().await?
    //     .args(&config.all_but_adm())
    //     .checked_status()
    //     .await?;

    delay_for(Duration::from_secs(30)).await;

    configure_docker_network(&server_list[..]).await?;

    add_docker_servers(&config, &server_map).await?;

    Ok(())
}

pub async fn configure_docker_network(hosts: &[&str]) -> Result<(), CmdError> {
    // The configure-docker-network provisioner must be run individually on
    // each server node.
    println!(
        "Configuring docker network for the following servers: {:?}",
        hosts
    );
    for host in hosts {
        provision_node(host, "configure-docker-network")
            .await?
            .checked_status()
            .await?;
    }

    Ok(())
}

async fn create_monitored_ldiskfs(config: &ClusterConfig) -> Result<(), CmdError> {
    pdsh::install_ldiskfs_no_iml(&config.storage_server_ips(), config.lustre_version()).await?;

    reload()
        .await?
        .args(config.storage_servers())
        .checked_status()
        .await?;

    for node in config.storage_servers() {
        println!("creating ldiskfs fs for {}", node);
        provision_node(node, "configure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2,mount-ldiskfs-fs,mount-ldiskfs-fs2")
            .await?
            .checked_status()
            .await?;
    }

    Ok(())
}

async fn create_monitored_zfs(config: &ClusterConfig) -> Result<(), CmdError> {
    pdsh::install_zfs_no_iml(&config.storage_server_ips(), config.lustre_version()).await?;

    reload()
        .await?
        .args(config.storage_servers())
        .checked_status()
        .await?;

    for node in config.storage_servers() {
        println!("creating zfs fs for {}", node);
        provision_node(
            node,
            "configure-lustre-network,create-pools,zfs-params,create-zfs-fs",
        )
        .await?
        .checked_status()
        .await?;
    }

    Ok(())
}

pub async fn create_fs(fs_type: FsType, config: &ClusterConfig) -> Result<(), CmdError> {
    match fs_type {
        FsType::LDISKFS => create_monitored_ldiskfs(&config).await?,
        FsType::ZFS => create_monitored_zfs(&config).await?,
    };

    Ok(())
}

pub async fn configure_rpm_setup(
    setup: &SetupConfigType,
    cluster_config: &ClusterConfig,
) -> Result<(), CmdError> {
    let config: String = setup.into();

    let vagrant_path = canonicalize("../vagrant/").await?;
    let mut config_path = vagrant_path.clone();
    config_path.push("local_settings.py");

    let mut file = File::create(config_path).await?;
    file.write_all(config.as_bytes()).await?;

    let setup_config: &SetupConfig = setup.into();
    if setup_config.use_stratagem {
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
        "sudo cp /vagrant/local_settings.py /usr/share/chroma-manager/ \
            && sudo chroma-config profile register /vagrant/stratagem-server.profile \
            && sudo chroma-config profile register /vagrant/stratagem-client.profile \
            && sudo systemctl restart iml-manager.target",
    )
    .await?
    .checked_status()
    .await?;

    Ok(())
}

pub struct ClusterConfig {
    manager: &'static str,
    mds: Vec<&'static str>,
    mds_ips: Vec<&'static str>,
    oss: Vec<&'static str>,
    oss_ips: Vec<&'static str>,
    clients: Vec<&'static str>,
    iscsi: &'static str,
    lustre_version: &'static str,
}

impl Default for ClusterConfig {
    fn default() -> Self {
        ClusterConfig {
            manager: "adm",
            mds: vec!["mds1", "mds2"],
            mds_ips: vec!["10.73.10.11", "10.73.10.12"],
            oss: vec!["oss1", "oss2"],
            oss_ips: vec!["10.73.10.21", "10.73.10.22"],
            clients: vec!["c1"],
            iscsi: "iscsi",
            lustre_version: "2.12.4",
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
    pub fn all_but_adm(&self) -> Vec<&str> {
        let mut xs = vec![self.iscsi];

        xs.extend(self.storage_servers());
        xs.extend(&self.clients);

        xs
    }
    pub fn storage_servers(&self) -> Vec<&str> {
        [&self.mds[..], &self.oss[..]].concat()
    }
    pub fn storage_server_ips(&self) -> Vec<&str> {
        [&self.mds_ips[..], &self.oss_ips[..]].concat()
    }
    pub fn mds_servers(&self) -> Vec<&str> {
        [&self.mds[..]].concat()
    }
    pub fn oss_servers(&self) -> Vec<&str> {
        [&self.oss[..]].concat()
    }
    pub fn client_servers(&self) -> Vec<&str> {
        [&self.clients[..]].concat()
    }
    pub fn lustre_version(&self) -> &str {
        self.lustre_version
    }
}
