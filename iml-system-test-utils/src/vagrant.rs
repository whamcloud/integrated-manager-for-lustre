// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    iml, ssh, get_local_server_names, try_command_n_times, ServerList as _, SetupConfig, SetupConfigType,
    STRATAGEM_CLIENT_PROFILE, STRATAGEM_SERVER_PROFILE,
};
use futures::future::try_join_all;
use iml_cmd::{CheckedCommandExt, CmdError};
use std::{collections::HashMap, env, str, time::Duration};
use tokio::{
    fs::{canonicalize, create_dir, remove_dir_all},
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

    try_command_n_times(3, 1, &mut x).await
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

pub async fn configure_manager_overrides(
    setup: &SetupConfigType,
    cluster_config: &ClusterConfig,
) -> Result<(), CmdError> {
    let config: String = setup.into();

    ssh::create_iml_config_dir(cluster_config.manager_ip).await?;

    ssh::set_manager_overrides(cluster_config.manager_ip, config.as_str()).await
}

pub async fn configure_agent_overrides(config: &ClusterConfig) -> Result<(), CmdError> {
    let hosts = &config.storage_server_ips()[..];
    let config = r#"RUST_LOG=debug
LOG_LEVEL=10"#;
    ssh::create_agent_config_dir(hosts).await?;

    ssh::set_agent_overrides(hosts, config).await
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

pub async fn wait_on_services_ready(config: &ClusterConfig) -> Result<(), CmdError> {
    let output =
        run_vm_command(config.manager, "systemctl list-dependencies iml-manager.target | tail -n +2 | awk '{print$2}' | awk '{print substr($1, 3)}' | grep -v iml-settings-populator.service").await?.checked_output().await?;

    let status_commands = str::from_utf8(&output.stdout)
        .expect("Couldn't parse service list")
        .lines()
        .map(|s| {
            tracing::debug!("checking status of service {}", s);
            let cmd = format!("systemctl status {}", s);

            async move {
                let mut cmd = ssh::ssh_exec_cmd(config.manager_ip, cmd.as_str()).await?;
                try_command_n_times(50, 3, &mut cmd).await?;

                Ok::<(), CmdError>(())
            }
        });

    try_join_all(status_commands).await?;

    Ok(())
}

fn vm_list_from_output(output: &str) -> Vec<String> {
    output
        .lines()
        .filter_map(|s| {
            s.split(' ')
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

    tracing::debug!("Powering off the following vm's: {:?}", vm_list);

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

    tracing::debug!("Unregistering the following vm's: {:?}", vm_list);

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

pub async fn clear_vbox_machine_folder() -> Result<(), CmdError> {
    let mut x = vbox_manage().await?;

    let out = x.arg("list").arg("systemproperties").output().await?;

    let properties = str::from_utf8(&out.stdout).expect("Couldn't get output.");

    let machine_folder: Option<&str> = properties
        .lines()
        .find(|s| s.find("Default machine folder:").is_some())
        .map(|x| {
            x.split(':')
                .last()
                .map(|x| x.trim())
                .expect("Couldn't find machine folder.")
        });

    if let Some(path) = machine_folder {
        tracing::debug!("removing contents from machine folder: {}", path);
        remove_dir_all(path).await?;
        create_dir(path).await?;
    } else {
        tracing::debug!("Couldn't determine vbox machine folder. Contents of vms directory will not be cleaned.");
    }

    Ok(())
}

pub async fn setup_bare(
    storage_and_client_hosts: &[&str],
    all_hosts: &[&str],
    config: &ClusterConfig,
    ntp_server: NtpServer,
) -> Result<(), CmdError> {
    up().await?.args(all_hosts).checked_status().await?;

    match ntp_server {
        NtpServer::HostOnly => {
            ssh::configure_ntp_for_host_only_if(&config.storage_server_ips()).await?
        }
        NtpServer::Adm => ssh::configure_ntp_for_adm(&config.storage_server_ips()).await?,
    };

    ssh::setup_agent_debug(&config.hosts_to_ips(&storage_and_client_hosts[..])[..]).await?;

    halt().await?.args(all_hosts).checked_status().await?;

    for x in all_hosts {
        snapshot_save(x, "bare").await?.checked_status().await?;
    }

    Ok(())
}

pub async fn setup_iml_install(
    storage_and_client_servers: &[&str],
    setup_config: &SetupConfigType,
    config: &ClusterConfig,
) -> Result<(), CmdError> {
    let all_hosts = [
        &vec![config.iscsi, config.manager][..],
        storage_and_client_servers,
    ]
    .concat();

    up().await?.arg(config.manager).checked_status().await?;

    configure_manager_overrides(setup_config, config).await?;

    match env::var("REPO_URI") {
        Ok(x) => {
            provision_node(config.manager, "install-iml-repouri")
                .await?
                .env("REPO_URI", x)
                .checked_status()
                .await?;
        }
        _ => {
            provision_node(config.manager, "install-iml-local")
                .await?
                .checked_status()
                .await?;
        }
    };

    setup_bare(storage_and_client_servers, &all_hosts, &config, NtpServer::Adm).await?;

    up().await?
        .arg(config.manager)
        .checked_status()
        .await?;

    configure_rpm_setup(setup_config, &config).await?;

    halt()
        .await?
        .arg(config.manager)
        .checked_status()
        .await?;

    for host in &all_hosts {
        snapshot_save(host, "iml-installed")
            .await?
            .checked_status()
            .await?;
    }

    tracing::debug!("Bringing up servers: {:?}", all_hosts);
    up().await?.args(&all_hosts).checked_status().await?;

    wait_on_services_ready(config).await?;

    Ok(())
}

pub async fn setup_deploy_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    setup_config: &SetupConfigType,
    server_map: HashMap<String, &[&str], S>,
) -> Result<(), CmdError> {
    setup_iml_install(&server_map.to_server_list(), &setup_config, &config).await?;

    configure_agent_overrides(config).await?;

    for (profile, hosts) in server_map {
        let host_ips = config.hosts_to_ips(&hosts);
        for host in host_ips {
            tracing::debug!("pinging host to make sure it is up.");
            ssh::ssh_exec(host, "uname -r").await?;
        }

        run_vm_command(
            config.manager,
            &format!("iml server add -h {} -p {}", get_local_server_names(hosts).join(","), profile),
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

    wait_on_services_ready(config).await?;

    Ok(())
}

pub async fn add_docker_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    server_map: &HashMap<String, &[&str], S>,
) -> Result<(), CmdError> {
    configure_agent_overrides(config).await?;

    iml::server_add(&server_map).await?;

    halt()
        .await?
        .args(&config.all_but_adm())
        .checked_status()
        .await?;

    for host in config.all_but_adm() {
        snapshot_save(host, "servers-deployed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?
        .args(&config.all_but_adm())
        .checked_status()
        .await
}

pub async fn configure_rpm_setup(
    setup: &SetupConfigType,
    cluster_config: &ClusterConfig,
) -> Result<(), CmdError> {
    let setup_config: &SetupConfig = setup.into();

    if setup_config.use_stratagem {
        ssh::create_iml_config_dir(cluster_config.manager_ip).await?;

        ssh::ssh_exec(
            cluster_config.manager_ip,
            format!(
                r#"cat <<EOF > {}
{}
EOF
"#,
                format!("{}/stratagem-server.profile", iml::IML_RPM_CONFIG_PATH),
                STRATAGEM_SERVER_PROFILE,
            )
            .as_str(),
        )
        .await?;

        ssh::ssh_exec(
            cluster_config.manager_ip,
            format!(
                r#"cat <<EOF > {}
{}
EOF
"#,
                format!("{}/stratagem-client.profile", iml::IML_RPM_CONFIG_PATH),
                STRATAGEM_CLIENT_PROFILE,
            )
            .as_str(),
        )
        .await?;

        run_vm_command(
            cluster_config.manager,
            format!(
                "sudo chroma-config profile register {}/stratagem-server.profile \
        && sudo chroma-config profile register {}/stratagem-client.profile \
        && sudo systemctl restart iml-manager.target",
                iml::IML_RPM_CONFIG_PATH,
                iml::IML_RPM_CONFIG_PATH
            )
            .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    Ok(())
}

pub async fn setup_deploy_docker_servers<S: std::hash::BuildHasher>(
    config: &ClusterConfig,
    server_map: HashMap<String, &[&str], S>,
) -> Result<(), CmdError> {
    let server_set: Vec<&str> = server_map.to_server_list();
    let all_hosts = [&vec![config.iscsi][..], &server_set].concat();

    setup_bare(&server_set, &all_hosts, &config, NtpServer::HostOnly).await?;

    up().await?.args(&all_hosts).checked_status().await?;

    delay_for(Duration::from_secs(60)).await;

    configure_docker_network(&server_set).await?;

    add_docker_servers(&config, &server_map).await?;

    Ok(())
}

pub async fn configure_docker_network(hosts: &[&str]) -> Result<(), CmdError> {
    // The configure-docker-network provisioner must be run individually on
    // each server node.
    tracing::debug!(
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
    ssh::install_ldiskfs_no_iml(&config.storage_server_ips(), config.lustre_version()).await?;

    reload()
        .await?
        .args(config.storage_servers())
        .checked_status()
        .await?;

    let xs = config
        .storage_servers()
        .into_iter()
        .map(|x| {
            tracing::debug!("creating ldiskfs fs for {}", x);
            async move {
                provision_node(x, "configure-lustre-network,create-ldiskfs-fs,create-ldiskfs-fs2,mount-ldiskfs-fs,mount-ldiskfs-fs2")
                    .await?
                    .checked_status()
                    .await?;

                Ok::<_, CmdError>(())
            }
        });

    try_join_all(xs).await?;

    Ok(())
}

async fn create_monitored_zfs(config: &ClusterConfig) -> Result<(), CmdError> {
    ssh::install_zfs_no_iml(&config.storage_server_ips(), config.lustre_version()).await?;

    reload()
        .await?
        .args(config.storage_servers())
        .checked_status()
        .await?;

    let xs = config.storage_servers().into_iter().map(|x| {
        tracing::debug!("creating zfs fs for {}", x);
        async move {
            provision_node(
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

pub async fn create_fs(fs_type: FsType, config: &ClusterConfig) -> Result<(), CmdError> {
    match fs_type {
        FsType::LDISKFS => create_monitored_ldiskfs(&config).await?,
        FsType::ZFS => create_monitored_zfs(&config).await?,
    };

    Ok(())
}

pub async fn remove_rpm_setup_files() {}

pub struct ClusterConfig {
    manager: &'static str,
    manager_ip: &'static str,
    mds: Vec<&'static str>,
    mds_ips: Vec<&'static str>,
    oss: Vec<&'static str>,
    oss_ips: Vec<&'static str>,
    client: Vec<&'static str>,
    client_ips: Vec<&'static str>,
    iscsi: &'static str,
    lustre_version: &'static str,
    server_map: HashMap<&'static str, &'static str>,
}

impl Default for ClusterConfig {
    fn default() -> Self {
        ClusterConfig {
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
            .collect::<HashMap<&str, &str>>(),
        }
    }
}

impl ClusterConfig {
    pub fn all(&self) -> Vec<&str> {
        let mut xs = vec![self.iscsi, self.manager];

        xs.extend(self.storage_servers());
        xs.extend(&self.client);

        xs
    }
    pub fn all_but_adm(&self) -> Vec<&str> {
        let mut xs = vec![self.iscsi];

        xs.extend(self.storage_servers());
        xs.extend(&self.client);

        xs
    }
    pub fn manager_ip(&self) -> Vec<&str> {
        vec![self.manager_ip]
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
        [&self.client[..]].concat()
    }
    pub fn client_server_ips(&self) -> Vec<&str> {
        [&self.client_ips[..]].concat()
    }
    pub fn lustre_version(&self) -> &str {
        self.lustre_version
    }
    pub fn hosts_to_ips(&self, hosts: &[&str]) -> Vec<&str> {
        hosts
            .into_iter()
            .map(|host| {
                self.server_map
                    .get(host)
                    .expect(format!("Couldn't locate {} in server map.", host).as_str())
            })
            .map(|x| *x)
            .collect()
    }
}
