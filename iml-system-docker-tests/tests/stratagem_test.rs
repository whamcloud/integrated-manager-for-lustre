// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod utils;

use iml_system_test_utils::{vagrant, SetupConfig, SetupConfigType, SystemdErrSos as _};
use iml_systemd::SystemdError;
use std::collections::{hash_map::RandomState, HashMap};
use utils::{run_fs_test, wait_for_ntp};

async fn run_test(config: &vagrant::ClusterConfig) -> Result<(), SystemdError> {
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::DdnAi400,
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

#[tokio::test]
async fn test_docker_stratagem_setup() -> Result<(), SystemdError> {
    let config = vagrant::ClusterConfig::default();

    run_test(&config)
        .await
        .handle_test_result(&config.storage_server_ips()[..], "docker_stratagem_test")
        .await
}
