// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_docker_tests::{run_fs_test, wait_for_ntp};
use iml_system_test_utils::{vagrant, SetupConfig, SetupConfigType, SystemTestError, WithSos as _};

async fn run_test(config: &vagrant::ClusterConfig) -> Result<(), SystemTestError> {
    run_fs_test(
        &config,
        &SetupConfigType::DockerSetup(SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::DDN(iml_wire_types::DdnBranding::Exascaler),
        }),
        vec![
            ("stratagem_server".into(), &config.mds_servers()[..]),
            ("base_monitored".into(), &config.oss_servers()[..]),
            ("stratagem_client".into(), &config.client_servers()[..]),
        ],
        vagrant::FsType::LDISKFS,
    )
    .await?;

    wait_for_ntp(&config).await?;

    // create 10 directories of 10 files
    ssh::ssh_exec(config.client_server_ips()[0], "for i in $(seq -w 0 10); do mkdir /mnt/fs/dir.$i; for j in $(seq -w 0 10); do dd if=/dev/null of=/mnt/fs/dir.$i/file.$j bs=1M count=1; done; done").await?;

    // run stratagem scan
    ssh::ssh_exec(config.manager_ip, "iml stratagem scan -r 1s -f fs").await?;

    let mut n: u32 = 0;

    // check output on client
    for ip in config.client_server_ips() {
        if let Ok((_, output)) = ssh::ssh_exec(ip, "wc -l /tmp/expiring_fids-fs-*.txt").await {
            assert_eq!(n, 0);
            n = output.stdout.parse();
            break;
        }
    }

    assert_eq!(n, 100);

    Ok(())
}

#[tokio::test]
async fn test_docker_stratagem_setup() -> Result<(), SystemTestError> {
    let config = vagrant::ClusterConfig::default();

    run_test(&config)
        .await
        .handle_test_result(
            &[
                &config.storage_server_ips()[..],
                &config.client_server_ips()[..],
            ]
            .concat(),
            "docker_stratagem_test",
        )
        .await
}
