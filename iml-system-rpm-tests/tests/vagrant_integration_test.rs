// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_test_utils::{get_local_server_names, iml, vagrant, SetupConfig};
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
    setup_config: &SetupConfig,
    server_map: HashMap<String, &[String], S>,
    fs_type: vagrant::FsType,
) -> Result<(), Box<dyn std::error::Error>> {
    setup().await?;

    vagrant::setup_deploy_servers(&config, &setup_config, server_map).await?;

    vagrant::create_fs(fs_type).await?;

    delay_for(Duration::from_secs(10)).await;

    iml::detect_fs().await?;

    Ok(())
}

#[tokio::test]
async fn test_ldiskfs_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();
    let server_names = get_local_server_names(&config.storage_servers());

    run_fs_test(
        &config,
        &SetupConfig {
            use_stratagem: false,
            branding: iml_wire_types::Branding::Whamcloud,
        },
        vec![("base_monitored".into(), &server_names[..])]
            .into_iter()
            .collect::<HashMap<String, &[String], RandomState>>(),
        vagrant::FsType::LDISKFS,
    )
    .await?;

    Ok(())
}

#[tokio::test]
async fn test_zfs_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();
    let server_names = get_local_server_names(&config.storage_servers());

    run_fs_test(
        &config,
        &SetupConfig {
            use_stratagem: false,
            branding: iml_wire_types::Branding::Whamcloud,
        },
        vec![("base_monitored".into(), &server_names[..])]
            .into_iter()
            .collect::<HashMap<String, &[String], RandomState>>(),
        vagrant::FsType::ZFS,
    )
    .await?;

    Ok(())
}

#[tokio::test]
async fn test_stratagem_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();
    run_fs_test(
        &config,
        &SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::Whamcloud,
        },
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

    Ok(())
}
