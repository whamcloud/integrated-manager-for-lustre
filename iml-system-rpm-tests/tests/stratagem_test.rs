// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_cli::api_utils::post;
use iml_system_rpm_tests::{run_fs_test, wait_for_ntp};
use iml_system_test_utils::{
    ssh, vagrant, SetupConfig, SetupConfigType, SystemTestError, WithSos as _,
};
use std::time::Duration;
use tokio::time::delay_for;

async fn run_test(config: &vagrant::ClusterConfig) -> Result<(), SystemTestError> {
    run_fs_test(
        &config,
        &SetupConfigType::RpmSetup(SetupConfig {
            use_stratagem: true,
            branding: iml_wire_types::Branding::Whamcloud,
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

    let task = r#"{"filesystem": 1, "name": "testfile", "state": "created", "keep_failed": false, "actions": [ "stratagem.warning" ], "single_runner": true, "args": { "report_file": "/tmp/test-taskfile.txt" } }"#;

    // create file
    let file_fut = ssh::ssh_exec(
        config.client_server_ips()[0],
        "touch /mnt/fs/reportfile; lfs path2fid /mnt/fs/reportfile",
    );

    // Create Task
    let task_fut = post("task", task);

    let ((_, output), _) = try_join(file_fut, task_fut).await?;

    let cmd = format!(
        "echo {} | socat - unix-connect:/run/iml/postman-testfile.sock",
        fid
    );

    ssh::ssh_exec(config.mds_server_ips()[0], cmd).await?;

    // @@ wait for fid to process by checking Task
    delay_for(Duration::from_secs(20)).await;

    let mut found = false;

    // check output on client
    for ip in config.client_server_ips() {
        if let Ok((_, output)) = ssh::ssh_exec(ip, "cat /tmp/test-taskfile.txt").await {
            assert_eq!(output.stdout, b#"/mnt/fs/reportfile\n"#);
            found = true;
            break;
        }
    }

    assert_eq!(found, true);

    Ok(())
}

#[tokio::test]
async fn test_stratagem_setup() -> Result<(), SystemTestError> {
    let config = vagrant::ClusterConfig::default();
    run_test(&config)
        .await
        .handle_test_result(
            &vec![
                &config.manager_ip()[..],
                &config.storage_server_ips()[..],
                &config.client_server_ips(),
            ]
            .concat()[..],
            "rpm_stratagem_test",
        )
        .await
}
