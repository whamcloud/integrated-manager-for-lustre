// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::{CheckedCommandExt, CmdError};
use iml_system_test_utils::{iml, vagrant, SetupConfig, SetupConfigType};
use std::{
    collections::{hash_map::RandomState, HashMap},
    time::Duration,
};
use tokio::time::delay_for;

async fn setup() -> Result<(), Box<dyn std::error::Error>> {
    vagrant::destroy().await?;

    Ok(())
}

async fn run_fs_test<S: std::hash::BuildHasher>(
    config: &vagrant::ClusterConfig,
    setup_config: &SetupConfigType,
    server_map: HashMap<String, &[&str], S>,
    fs_type: vagrant::FsType,
) -> Result<(), Box<dyn std::error::Error>> {
    setup().await?;

    vagrant::setup_deploy_servers(&config, &setup_config, server_map).await?;

    vagrant::create_fs(fs_type).await?;

    delay_for(Duration::from_secs(30)).await;

    iml::detect_fs().await?;

    Ok(())
}

async fn wait_for_ntp(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    vagrant::provision("wait-for-ntp")
        .await?
        .args(&config.storage_servers()[..])
        .checked_status()
        .await?;

    Ok(())
}

#[tokio::test]
async fn test_ldiskfs_setup() -> Result<(), Box<dyn std::error::Error>> {
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
async fn test_zfs_setup() -> Result<(), Box<dyn std::error::Error>> {
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
async fn test_stratagem_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();
    run_fs_test(
        &config,
        &SetupConfigType::RpmSetup(SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::Whamcloud,
        }),
        vec![
            ("stratagem_server".into(), &config.get_mds_servers()[..]),
            ("base_monitored".into(), &config.get_oss_servers()[..]),
            ("stratagem_client".into(), &config.get_client_servers()[..]),
        ]
        .into_iter()
        .collect::<HashMap<String, &[&str], RandomState>>(),
        vagrant::FsType::LDISKFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}
