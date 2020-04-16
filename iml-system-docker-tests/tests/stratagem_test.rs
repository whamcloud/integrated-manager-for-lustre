// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_docker_tests::{run_fs_test, wait_for_ntp};
use iml_system_test_utils::*;

async fn run_test(config: Config) -> Result<(), SystemTestError> {
    let config = run_fs_test(config).await?;

    wait_for_ntp(&config).await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_stratagem_setup() -> Result<(), SystemTestError> {
    let config: Config = Config::default();
    let config: Config = Config {
        profile_map: vec![
            ("stratagem_server".into(), config.mds_servers()),
            ("base_monitored".into(), config.oss_servers()),
            ("stratagem_client".into(), config.client_servers()),
        ],
        use_stratagem: true,
        branding: iml_wire_types::Branding::DDN(iml_wire_types::DdnBranding::Exascaler),
        test_type: TestType::Docker,
        ntp_server: NtpServer::HostOnly,
        ..config
    };

    let result_servers: Vec<&str> = [
        &config.storage_server_ips()[..],
        &config.client_server_ips()[..],
    ]
    .concat();

    run_test(config)
        .await
        .handle_test_result(result_servers, "docker_stratagem_test")
        .await
}
