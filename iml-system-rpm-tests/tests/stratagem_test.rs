// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_rpm_tests::run_fs_test;
use iml_system_test_utils::*;

#[tokio::test]
async fn test_stratagem_setup() -> Result<(), TestError> {
    let config = Config::default();
    let config: Config = Config {
        profile_map: vec![
            ("base_monitored", config.storage_servers()),
            ("stratagem_client", config.client_servers()),
        ],
        branding: iml_wire_types::Branding::DDN(iml_wire_types::DdnBranding::Exascaler),
        use_stratagem: true,
        ..config
    };

    let result_servers = config.manager_and_storage_server_and_client_ips();

    run_fs_test(config)
        .await
        .handle_test_result(result_servers, "rpm_stratagem_test")
        .await?;

    Ok(())
}
