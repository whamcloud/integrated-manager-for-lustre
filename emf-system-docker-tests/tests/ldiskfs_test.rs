// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_system_docker_tests::run_fs_test;
use emf_system_test_utils::*;

#[tokio::test]
async fn test_docker_ldiskfs_setup() -> Result<(), TestError> {
    let config: Config = Config::default();
    let config: Config = Config {
        profile_map: vec![
            ("base_monitored".into(), config.storage_servers()),
            ("base_client".into(), config.client_servers()),
        ],
        test_type: TestType::Docker,
        ..config
    };

    let result_servers = config.manager_and_storage_server_ips();

    run_fs_test(config)
        .await
        .handle_test_result(result_servers, "docker_ldiskfs_test")
        .await?;

    Ok(())
}
