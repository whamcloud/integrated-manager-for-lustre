// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use iml_system_docker_tests::{run_fs_test, wait_for_ntp};
use iml_system_test_utils::*;

async fn run_test(config: Config) -> Result<(), CmdError> {
    let config = run_fs_test(config).await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_zfs_setup() -> Result<(), CmdError> {
    let config: Config = Config::default();
    let config: Config = Config {
        profile_map: vec![("base_monitored".into(), config.storage_servers())],
        test_type: TestType::Docker,
        ntp_server: NtpServer::HostOnly,
        fs_type: FsType::ZFS,
        ..config
    };

    let result_servers = config.manager_and_storage_server_ips();

    run_test(config)
        .await
        .handle_test_result(result_servers, "docker_zfs_test")
        .await
}
