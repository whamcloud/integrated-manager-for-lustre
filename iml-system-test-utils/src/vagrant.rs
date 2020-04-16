// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::*;
use futures::future::try_join_all;
use iml_cmd::{CheckedCommandExt, CmdError};
use std::{env, str, time::Duration};
use tokio::{
    fs::{canonicalize, create_dir, remove_dir_all, File},
    io::AsyncWriteExt,
    process::Command,
    time::delay_for,
};

pub async fn vagrant() -> Result<Command, CmdError> {
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

pub async fn destroy<'a>(config: &Config) -> Result<(), CmdError> {
    let nodes = config.destroy_list();

    for node in &nodes {
        let mut suspend_cmd = suspend().await?;
        suspend_cmd.arg(node);

        try_command_n_times(3, 1, &mut suspend_cmd).await?;
    }

    for node in &nodes {
        let mut destroy_cmd = vagrant().await?;
        destroy_cmd.arg("destroy").arg("-f").arg(node);

        try_command_n_times(3, 1, &mut destroy_cmd).await?;
    }

    Ok(())
}

pub async fn halt() -> Result<Command, CmdError> {
    let mut x = vagrant().await?;
    x.arg("halt");

    Ok(x)
}

pub async fn suspend() -> Result<Command, CmdError> {
    let mut x = vagrant().await?;
    x.arg("suspend");

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

pub async fn detect_fs(config: &Config) -> Result<(), CmdError> {
    run_vm_command(config.manager, "iml filesystem detect")
        .await?
        .checked_status()
        .await
}

pub async fn global_prune() -> Result<(), CmdError> {
    let mut x = vagrant().await?;

    x.arg("global-status").arg("--prune").checked_status().await
}

pub async fn wait_on_services_ready(config: &Config) -> Result<(), CmdError> {
    let output =
        run_vm_command(config.manager, "systemctl list-dependencies iml-manager.target | tail -n +2 | awk '{print$2}' | awk '{print substr($1, 3)}' | grep -v iml-settings-populator.service | grep -v iml-sfa.service").await?.checked_output().await?;

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

pub async fn setup_bare(config: Config) -> Result<Config, CmdError> {
    if config.test_type == TestType::Rpm {
        up().await?.arg(config.manager).checked_status().await?;

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
    }

    up().await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    match config.ntp_server {
        NtpServer::HostOnly => {
            ssh::configure_ntp_for_host_only_if(config.storage_server_ips()).await?
        }
        NtpServer::Adm => ssh::configure_ntp_for_adm(config.storage_server_ips()).await?,
    };

    halt()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    for x in config.all_hosts() {
        snapshot_save(
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
    up().await?
        .args(&vec![config.manager][..])
        .checked_status()
        .await?;

    configure_rpm_setup(&config).await?;

    halt()
        .await?
        .args(&vec![config.manager][..])
        .checked_status()
        .await?;

    for host in config.all_hosts() {
        snapshot_save(
            host,
            snapshots::get_snapshot_name_for_state(&config, TestState::Configured)
                .to_string()
                .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    up().await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    wait_on_services_ready(&config).await?;

    Ok(config)
}

pub async fn deploy_servers(config: Config) -> Result<Config, CmdError> {
    for (profile, hosts) in &config.profile_map {
        let host_ips = config.hosts_to_ips(&hosts);
        for host in host_ips {
            tracing::debug!("pinging host to make sure it is up.");
            ssh::ssh_exec(host, "uname -r").await?;
        }

        run_vm_command(
            config.manager,
            &format!("iml server add -p {} {}", profile, hosts.join(",")),
        )
        .await?
        .checked_status()
        .await?;
    }

    halt()
        .await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    for host in config.all_hosts() {
        snapshot_save(
            host,
            snapshots::get_snapshot_name_for_state(&config, TestState::ServersDeployed)
                .to_string()
                .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    up().await?
        .args(config.all_hosts())
        .checked_status()
        .await?;

    wait_on_services_ready(&config).await?;

    Ok(config)
}

pub async fn add_docker_servers(config: &Config) -> Result<(), CmdError> {
    iml::server_add(&config).await?;

    halt()
        .await?
        .args(&config.all_hosts())
        .checked_status()
        .await?;

    for host in config.all_hosts() {
        snapshot_save(
            host,
            snapshots::get_snapshot_name_for_state(&config, TestState::ServersDeployed)
                .to_string()
                .as_str(),
        )
        .await?
        .checked_status()
        .await?;
    }

    up().await?.args(&config.all_hosts()).checked_status().await
}

pub async fn deploy_docker_servers(config: Config) -> Result<Config, CmdError> {
    up().await?
        .args(&config.all_hosts())
        .checked_status()
        .await?;

    delay_for(Duration::from_secs(30)).await;

    configure_docker_network(&config).await?;

    add_docker_servers(&config).await?;

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
        provision_node(host, "configure-docker-network")
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

async fn create_monitored_zfs(config: &Config) -> Result<(), CmdError> {
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

    Ok(config)
}

pub async fn create_fs(config: Config) -> Result<Config, CmdError> {
    match config.fs_type {
        FsType::LDISKFS => create_monitored_ldiskfs(&config).await?,
        FsType::ZFS => create_monitored_zfs(&config).await?,
    };

    delay_for(Duration::from_secs(30)).await;

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

    rsync(config.manager).await?;

    run_vm_command(config.manager, vm_cmd.as_str())
        .await?
        .checked_status()
        .await?;

    Ok(())
}
