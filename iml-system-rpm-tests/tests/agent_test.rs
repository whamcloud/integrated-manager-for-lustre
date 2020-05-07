// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_system_rpm_tests::{run_fs_test, wait_for_ntp};
use iml_system_test_utils::{vagrant, SetupConfig, SetupConfigType, SystemTestError, WithSos as _};
use std::collections::HashMap;

#[tokio::test]
async fn test_ldiskfs_setup() -> Result<(), SystemTestError> {
    let config = vagrant::ClusterConfig::default();
    
    vagrant::configure_agent_dropins(&config).await?;
}
