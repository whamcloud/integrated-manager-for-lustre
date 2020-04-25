// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod utils;

use iml_cmd::CmdError;
use iml_system_test_utils::{vagrant, CmdErrSos as _, SetupConfig, SetupConfigType};
use std::collections::{hash_map::RandomState, HashMap};
use utils::{run_fs_test, wait_for_ntp};

async fn run_test(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
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
async fn test_ldiskfs_setup() -> Result<(), iml_cmd::CmdError> {
    let config = vagrant::ClusterConfig::default();
    run_test(&config)
        .await
        .handle_test_result(
            &vec![&config.manager_ip()[..], &config.storage_server_ips()[..]].concat()[..],
            "rpm_ldiskfs_test",
        )
        .await
}
