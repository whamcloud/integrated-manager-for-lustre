// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate emf_corosync;

use emf_corosync::{
    fetch_corosync_cluster_by_nodes, upsert_corosync_cluster, CorosyncNodeKey, EmfCorosyncError,
};
use emf_postgres::test_setup;

#[tokio::test]
#[ignore = "Requires an active and populated DB"]
async fn test_insert() -> Result<(), EmfCorosyncError> {
    let pool = test_setup().await?;

    let key = CorosyncNodeKey {
        id: "Food".to_string(),
        name: "Bard".to_string(),
    }
    .to_string();

    let key2 = CorosyncNodeKey {
        id: "Food2".to_string(),
        name: "Bard2".to_string(),
    }
    .to_string();

    let xs = vec![key, key2];

    upsert_corosync_cluster(&xs, &pool).await?;

    fetch_corosync_cluster_by_nodes(&xs, &pool).await?;

    Ok(())
}
