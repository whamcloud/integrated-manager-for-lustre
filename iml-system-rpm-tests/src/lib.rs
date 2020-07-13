// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::{CheckedCommandExt, CmdError};
use iml_system_test_utils::*;
use tracing::Level;
use tracing_subscriber::fmt::Subscriber;

pub async fn setup() -> Result<(), CmdError> {
    Subscriber::builder().with_max_level(Level::DEBUG).init();

    Ok(())
}

pub async fn cleanup(config: &Config) -> Result<(), CmdError> {
    vagrant::destroy(config).await?;
    vagrant::global_prune().await?;
    vagrant::poweroff_running_vms().await?;
    vagrant::unregister_vms().await?;
    vagrant::clear_vbox_machine_folder().await?;

    Ok(())
}

pub async fn run_fs_test(config: Config) -> Result<Config, CmdError> {
    setup().await?;

    let snapshot_map = snapshots::get_snapshots().await?;
    let graph = snapshots::create_graph(&snapshot_map["iscsi"], &config);
    let active_snapshots = snapshots::get_active_snapshots(&config, &graph);
    let target_snapshot = active_snapshots.last().expect("target snapshot not found.");
    println!("target snapshot: {:?}", target_snapshot);

    if target_snapshot.name != snapshots::SnapshotName::Init {
        vagrant::halt()
            .await?
            .args(&config.all_hosts())
            .checked_status()
            .await?;

        for host in config.all_hosts() {
            let result = vagrant::snapshot_restore(host, target_snapshot.name.to_string().as_str())
                .await?
                .checked_status()
                .await;

            if result.is_err() {
                println!(
                    "Snapshot {} not available on host {}. Skipping.",
                    target_snapshot.name.to_string(),
                    host
                );
            }
        }
    }

    let actions = snapshots::get_active_test_path(&config, &graph, &target_snapshot.name);

    let mut config = config;
    for action in actions {
        config = (graph[action].transition)(config).await?;
    }

    Ok(config)
}

pub async fn wait_for_ntp(config: &Config) -> Result<(), CmdError> {
    ssh::wait_for_ntp_for_adm(&config.storage_server_ips()).await?;

    Ok(())
}
