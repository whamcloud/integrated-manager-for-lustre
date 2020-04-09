// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::{CheckedCommandExt, CmdError};
use iml_system_test_utils::{
    docker, get_local_server_names, iml, vagrant, SetupConfig, SetupConfigType,
};
use std::{
    collections::{hash_map::RandomState, HashMap},
    time::Duration,
};
use tokio::time::delay_for;

async fn setup() -> Result<(), Box<dyn std::error::Error>> {
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

    Ok(())
}

async fn run_fs_test<S: std::hash::BuildHasher>(
    config: &vagrant::ClusterConfig,
    docker_setup: &SetupConfigType,
    server_map: HashMap<String, &[String], S>,
    fs_type: vagrant::FsType,
) -> Result<(), Box<dyn std::error::Error>> {
    setup().await?;
    docker::configure_docker_setup(&docker_setup).await?;

    docker::deploy_iml_stack().await?;

    vagrant::setup_deploy_docker_servers(&config, server_map).await?;

    vagrant::create_fs(fs_type).await?;

    delay_for(Duration::from_secs(10)).await;

    iml::detect_fs().await?;

    Ok(())
}

async fn wait_for_ntp(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    vagrant::provision("wait-for-ntp-docker")
        .await?
        .args(&config.storage_servers()[..])
        .checked_status()
        .await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_ldiskfs_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();
    let server_names = get_local_server_names(&config.storage_servers());
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: false,
            branding: iml_wire_types::Branding::Whamcloud,
        }),
        vec![("base_monitored".into(), &server_names[..])]
            .into_iter()
            .collect::<HashMap<String, &[String], RandomState>>(),
        vagrant::FsType::LDISKFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_zfs_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();
    let server_names = get_local_server_names(&config.storage_servers());
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: false,
            branding: iml_wire_types::Branding::Whamcloud,
        }),
        vec![("base_monitored".into(), &server_names[..])]
            .into_iter()
            .collect::<HashMap<String, &[String], RandomState>>(),
        vagrant::FsType::ZFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_stratagem_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::DdnAi400,
        }),
        vec![
            (
                "stratagem_server".into(),
                &get_local_server_names(&config.get_mds_servers())[..],
            ),
            (
                "base_monitored".into(),
                &get_local_server_names(&config.get_oss_servers())[..],
            ),
            (
                "stratagem_client".into(),
                &get_local_server_names(&config.get_client_servers())[..],
            ),
        ]
        .into_iter()
        .collect::<HashMap<String, &[String], RandomState>>(),
        vagrant::FsType::LDISKFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}
