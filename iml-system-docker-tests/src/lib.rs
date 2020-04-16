// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use iml_system_test_utils::*;
use iml_systemd::SystemdError;
use tracing::Level;
use tracing_subscriber::fmt::Subscriber;

pub async fn setup(config: &Config) -> Result<(), SystemdError> {
    Subscriber::builder().with_max_level(Level::DEBUG).init();

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
    vagrant::destroy(config).await?;
    vagrant::global_prune().await?;
    vagrant::poweroff_running_vms().await?;
    vagrant::unregister_vms().await?;
    vagrant::clear_vbox_machine_folder().await?;

    Ok(())
}

pub async fn run_fs_test(config: Config) -> Result<Config, SystemdError> {
    setup(&config).await?;

    let config = vagrant::setup_bare(config).await?;

    let config = docker::configure_docker_setup(config).await?;

    docker::deploy_iml_stack().await?;

    let config = vagrant::deploy_docker_servers(config).await?;

    let config = vagrant::install_fs(config).await?;

    let config = vagrant::create_fs(config).await?;

    iml::detect_fs().await?;

    Ok(config)
}

pub async fn wait_for_ntp(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    ssh::wait_for_ntp_for_host_only_if(&config.storage_server_ips()).await?;

    Ok(())
}
