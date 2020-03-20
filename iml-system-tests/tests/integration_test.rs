// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod common;
use common::{docker, iml, vagrant};

#[tokio::test]
async fn test_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();

    vagrant::setup_deploy_servers(&config, "base_managed_patchless").await?;

    Ok(())
}

#[tokio::test]
async fn test_docker_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();

    docker::volume_prune().await?;
    docker::network_prune().await?;

    docker::deploy_iml_stack().await?;
    docker::wait_for_iml_stack().await?;
    
    vagrant::setup_deploy_docker_servers(&config, "base_monitored").await?;
    vagrant::configure_ntp_for_host_only_if(&config).await?;
    vagrant::create_monitored_ldiskfs(&config).await?;

    iml::detect_fs().await?;

    Ok(())
}
