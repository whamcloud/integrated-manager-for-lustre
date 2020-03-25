// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_test_utils::{docker, iml, vagrant};
use iml_systemd;

#[tokio::test]
async fn test_docker_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();

    // remove the stack if it is running and clean up volumes and network
    docker::remove_iml_stack().await?;
    docker::system_prune().await?;
    docker::volume_prune().await?;
    docker::configure_docker_overrides().await?;
    iml_systemd::restart_unit("docker.service".into()).await?;

    // Destroy any vagrant nodes that are currently running
    vagrant::destroy().await?;

    docker::deploy_iml_stack().await?;

    vagrant::setup_deploy_docker_servers(&config, "base_monitored").await?;
    vagrant::configure_ntp_for_host_only_if(&config).await?;
    vagrant::create_monitored_ldiskfs(&config).await?;

    iml::detect_fs().await?;

    Ok(())
}