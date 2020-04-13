// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use iml_system_test_utils::{pdsh, vagrant, SetupConfig, SetupConfigType};
use std::{
    collections::{hash_map::RandomState, HashMap},
    time::Duration,
};
use tokio::time::delay_for;

async fn setup() -> Result<(), CmdError> {
    vagrant::destroy().await?;
    vagrant::global_prune().await?;
    vagrant::poweroff_running_vms().await?;
    vagrant::unregister_vms().await?;

    Ok(())
}

async fn run_fs_test<S: std::hash::BuildHasher>(
    config: &vagrant::ClusterConfig,
    setup_config: &SetupConfigType,
    server_map: HashMap<String, &[&str], S>,
    fs_type: vagrant::FsType,
) -> Result<(), CmdError> {
    setup().await?;

    vagrant::setup_deploy_servers(&config, &setup_config, server_map).await?;

    vagrant::create_fs(fs_type, &config).await?;

    delay_for(Duration::from_secs(30)).await;

    vagrant::detect_fs(&config).await?;

    Ok(())
}

async fn wait_for_ntp(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    pdsh::wait_for_ntp_for_adm(&config.storage_server_ips()).await?;

    Ok(())
}

#[tokio::test]
async fn test_ldiskfs_setup() -> Result<(), CmdError> {
    let config = vagrant::ClusterConfig::default();

    run_fs_test(
        &config,
        &SetupConfigType::RpmSetup(SetupConfig {
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
async fn test_zfs_setup() -> Result<(), CmdError> {
    let config = vagrant::ClusterConfig::default();

    run_fs_test(
        &config,
        &SetupConfigType::RpmSetup(SetupConfig {
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
async fn test_stratagem_setup() -> Result<(), CmdError> {
    let config = vagrant::ClusterConfig::default();
    run_fs_test(
        &config,
        &SetupConfigType::RpmSetup(SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::Whamcloud,
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
