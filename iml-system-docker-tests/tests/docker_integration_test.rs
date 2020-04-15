// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use iml_system_test_utils::{docker, iml, pdsh, vagrant, SetupConfig, SetupConfigType};
use iml_systemd::SystemdError;
use std::{
    collections::{hash_map::RandomState, HashMap},
    time::Duration,
};
use tokio::time::delay_for;

async fn setup() -> Result<(), SystemdError> {
    // remove the stack if it is running and clean up volumes and network
    docker::remove_iml_stack().await?;
    docker::system_prune().await?;
    docker::volume_prune().await?;
    docker::configure_docker_overrides().await?;
    docker::stop_swarm().await?;
    docker::remove_password().await?;
    iml_systemd::restart_unit("docker.service".into()).await?;

    docker::start_swarm().await?;
    docker::set_password().await?;

    // Destroy any vagrant nodes that are currently running
    vagrant::destroy().await?;
    vagrant::destroy().await?;
    vagrant::global_prune().await?;
    vagrant::poweroff_running_vms().await?;
    vagrant::unregister_vms().await?;
    vagrant::clear_vbox_machine_folder().await?;

    Ok(())
}

async fn run_fs_test<S: std::hash::BuildHasher>(
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

    delay_for(Duration::from_secs(30)).await;

    iml::detect_fs().await?;

    Ok(())
}

async fn wait_for_ntp(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    pdsh::wait_for_ntp_for_host_only_if(&config.storage_server_ips()).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_ldiskfs_setup() -> Result<(), SystemdError> {
    let config = vagrant::ClusterConfig::default();
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: false,
            branding: iml_wire_types::Branding::Whamcloud,
        }),
        vec![("base_monitored".into(), &config.storage_servers()[..])]
            .into_iter()
            .collect::<HashMap<String, &[&str], RandomState>>(),
        vagrant::FsType::LDISKFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_zfs_setup() -> Result<(), SystemdError> {
    let config = vagrant::ClusterConfig::default();
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: false,
            branding: iml_wire_types::Branding::Whamcloud,
        }),
        vec![("base_monitored".into(), &config.storage_servers()[..])]
            .into_iter()
            .collect::<HashMap<String, &[&str], RandomState>>(),
        vagrant::FsType::ZFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_stratagem_setup() -> Result<(), SystemdError> {
    let config = vagrant::ClusterConfig::default();
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::DdnAi400,
        }),
        vec![
            ("stratagem_server".into(), &config.mds_servers()[..]),
            ("base_monitored".into(), &config.oss_servers()[..]),
            ("stratagem_client".into(), &config.client_servers()[..]),
        ]
        .into_iter()
        .collect::<HashMap<String, &[&str], RandomState>>(),
        vagrant::FsType::LDISKFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}
