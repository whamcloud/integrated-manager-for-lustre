// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod vagrant;

#[tokio::test]
async fn test_setup() -> Result<(), Box<dyn std::error::Error>> {
    let config = vagrant::ClusterConfig::default();

    vagrant::setup_deploy_servers(&config, "base_managed_patchless").await?;

    Ok(())
}
