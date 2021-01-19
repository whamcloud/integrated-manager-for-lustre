// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_cmd::CheckedCommandExt;
use emf_system_test_utils::*;
use tracing::Level;
use tracing_subscriber::fmt::Subscriber;

pub async fn run_fs_test(config: Config) -> Result<Config, TestError> {
    Subscriber::builder().with_max_level(Level::DEBUG).init();

    let snapshot_map = snapshots::get_snapshots().await?;
    let graph = snapshots::create_graph(&snapshot_map["iscsi"]);
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
