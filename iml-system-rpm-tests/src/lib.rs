// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use iml_system_test_utils::{ssh, vagrant, SetupConfigType};
use std::time::Duration;
use tokio::time::delay_for;
use tracing::Level;
use tracing_subscriber::fmt::Subscriber;

pub async fn setup(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    Subscriber::builder().with_max_level(Level::DEBUG).init();

    vagrant::destroy(config).await?;
    vagrant::global_prune().await?;
    vagrant::poweroff_running_vms().await?;
    vagrant::unregister_vms().await?;
    vagrant::clear_vbox_machine_folder().await?;

    Ok(())
}

pub async fn run_fs_test(
    config: &vagrant::ClusterConfig,
    setup_config: &SetupConfigType,
    server_map: Vec<(String, &[&str])>,
    fs_type: vagrant::FsType,
) -> Result<(), CmdError> {
    setup(config).await?;

    vagrant::setup_deploy_servers(&config, &setup_config, server_map).await?;

    vagrant::create_fs(fs_type, &config).await?;

    delay_for(Duration::from_secs(30)).await;

    vagrant::detect_fs(&config).await?;

    Ok(())
}

pub async fn wait_for_ntp(config: &vagrant::ClusterConfig) -> Result<(), CmdError> {
    ssh::wait_for_ntp(&config.storage_server_ips()).await?;

    Ok(())
}
