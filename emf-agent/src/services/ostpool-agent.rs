// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! OST pool agent service
//!
//!

use emf_agent::{
    action_plugins::ostpool::pools,
    agent_error::EmfAgentError,
    env,
    lustre::list_mdt0s,
    util::{create_filtered_writer, UnboundedSenderExt},
};
use emf_wire_types::{FsPoolMap, OstPool};
use futures::future::join_all;
use std::{collections::BTreeSet, time::Duration};
use tokio::time::interval;

/// List all Lustre Filesystems with MDT0 on this host
async fn list_fs() -> Vec<String> {
    list_mdt0s()
        .await
        .iter()
        .filter_map(|x| x.split("-MDT").next())
        .map(|x| x.to_string())
        .collect()
}

async fn get_fsmap(fsname: String) -> (String, BTreeSet<OstPool>) {
    let xs = pools(fsname.clone())
        .await
        .unwrap_or_else(|_| vec![])
        .into_iter()
        .collect();
    (fsname, xs)
}

async fn build_tree() -> FsPoolMap {
    let fslist = list_fs().await;

    join_all(fslist.into_iter().map(get_fsmap))
        .await
        .into_iter()
        .collect()
}

#[tokio::main]
async fn main() -> Result<(), EmfAgentError> {
    emf_tracing::init();

    let mut x = interval(Duration::from_secs(5));

    let port = env::get_port("OSTPOOL_AGENT_OSTPOOL_SERVICE_PORT");

    let writer = create_filtered_writer(port)?;

    loop {
        x.tick().await;

        let x = build_tree().await;

        let _ = writer.send_msg(x);
    }
}
