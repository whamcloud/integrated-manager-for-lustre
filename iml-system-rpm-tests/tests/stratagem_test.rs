// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_rpm_tests::{run_fs_test, wait_for_ntp};
use iml_system_test_utils::{WithSos as _, *};

async fn run_test(config: Config) -> Result<(), SystemTestError> {
    let config = run_fs_test(config).await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_stratagem_setup() -> Result<(), SystemTestError> {
    let config = Config::default();
    let config: Config = Config {
        profile_map: vec![
            ("stratagem_server".into(), config.mds_servers()),
            ("base_monitored".into(), config.oss_servers()),
            ("stratagem_client".into(), config.client_servers()),
        ],
        branding: iml_wire_types::Branding::DDN(iml_wire_types::DdnBranding::Exascaler),
        use_stratagem: true,
        ..config
    };

    let result_servers = vec![
        config.manager_ip(),
        config.storage_server_ips(),
        config.client_server_ips(),
    ]
    .concat();

    run_test(config)
        .await
        .handle_test_result(result_servers, "rpm_stratagem_test")
        .await?;

    Ok(())
}
