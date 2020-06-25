// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_docker_tests::{run_fs_test, wait_for_ntp};
use iml_system_test_utils::{vagrant, SetupConfig, SetupConfigType, SystemTestError, WithSos as _};

async fn run_test(config: &vagrant::ClusterConfig) -> Result<(), SystemTestError> {
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: false,
            branding: iml_wire_types::Branding::Whamcloud,
        }),
        vec![("base_monitored".into(), &config.storage_servers()[..])],
        vagrant::FsType::ZFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_zfs_setup() -> Result<(), SystemTestError> {
    let config = vagrant::ClusterConfig::default();

    run_test(&config)
        .await
        .handle_test_result(true, &config.storage_server_ips()[..], "docker_zfs_test")
        .await
}
