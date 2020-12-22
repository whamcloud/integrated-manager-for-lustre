// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_rpm_tests::run_fs_test;
use iml_system_test_utils::*;

#[tokio::test]
async fn test_ldiskfs_setup() -> Result<(), TestError> {
    let config: Config = Config::default();

    let config = Config {
        profile_map: vec![
            ("base_monitored", config.storage_servers()),
            ("base_client", config.client_servers()),
        ],
        ..config
    };

    let result_servers = config.manager_and_storage_server_ips();

    run_fs_test(config)
        .await
        .handle_test_result(result_servers, "rpm_ldiskfs_test")
        .await?;

    Ok(())
}
