// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use iml_system_test_utils::{docker, iml, ssh, vagrant, SetupConfigType};
use iml_systemd::SystemdError;
use std::{collections::HashMap, time::Duration};
use tokio::time::delay_for;

pub async fn setup() -> Result<(), SystemdError> {
    // remove the stack if it is running and clean up volumes and network
    docker::remove_iml_stack().await?;
    docker::system_prune().await?;
    docker::volume_prune().await?;
    docker::configure_docker_overrides().await?;
    docker::stop_swarm().await?;
    docker::remove_password().await?;

    docker::start_swarm().await?;
    docker::set_password().await?;

    // Destroy any vagrant nodes that are currently running
    vagrant::destroy().await?;
    vagrant::global_prune().await?;
    vagrant::poweroff_running_vms().await?;
    vagrant::unregister_vms().await?;
    vagrant::clear_vbox_machine_folder().await?;

    Ok(())
}

pub async fn run_fs_test<S: std::hash::BuildHasher>(
    config: &vagrant::ClusterConfig,
    docker_setup: &SetupConfigType,
    server_map: HashMap<String, &[&str], S>,
    fs_type: vagrant::FsType,
) -> Result<(), SystemdError> {
    setup().await?;
    docker::configure_docker_setup(&docker_setup).await?;

    docker::deploy_iml_stack().await?;

    vagrant::setup_deploy_docker_servers(&config, server_map).await?;

    vagrant::create_fs(fs_type, &config).await?;

    delay_for(Duration::from_secs(90)).await;

    iml::detect_fs().await?;

    Ok(())
}

pub async fn wait_for_ntp(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    ssh::wait_for_ntp(&config.storage_server_ips()).await?;

    Ok(())
}
