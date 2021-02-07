// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Snapshot listing agent service
//!
//! This module is responsible for continually discovering snapshots of filesystems.
//!
//!

use emf_agent::{
    action_plugins::lustre::snapshot, agent_error::EmfAgentError, device_scanner_client, env,
    lustre::list_mdt0s, util::create_filtered_writer,
};
use emf_wire_types::snapshot::{List, Snapshot};
use futures::{future::try_join_all, TryFutureExt};
use std::{
    collections::{HashMap, HashSet},
    time::Duration,
};
use tokio::time::interval;

async fn list() -> Result<Option<HashMap<String, Vec<Snapshot>>>, EmfAgentError> {
    // list the mounts
    // remove any mdt0's that are snapshots
    let snapshot_mounts = device_scanner_client::get_snapshot_mounts()
        .await?
        .into_iter()
        .filter_map(|x| {
            let s = x.opts.0.split(',').find(|x| x.starts_with("svname="))?;

            let s = s.split('=').nth(1)?;

            Some(s.to_string())
        })
        .collect::<HashSet<String>>();

    tracing::debug!("snapshot mounts {:?}", snapshot_mounts);

    let xs = list_mdt0s().await.into_iter().collect::<HashSet<String>>();
    let xs = xs
        .difference(&snapshot_mounts)
        .map(|x| x.to_string())
        .collect::<Vec<String>>();

    tracing::debug!("mdt0s: {:?}", &xs);

    if xs.is_empty() {
        tracing::debug!("No mdt0's. Returning `None`.");

        return Ok(None);
    }

    let xs = xs.into_iter().map(|x| async move {
        let fs_name = x.rsplitn(2, '-').nth(1);
        tracing::debug!("fs_name is: {:?}", fs_name);

        if let Some(fs_name) = fs_name {
            snapshot::list(List {
                target: x.to_string(),
                name: None,
            })
            .inspect_err(|x| {
                tracing::debug!("Error calling snapshot list: {:?}", x);
            })
            .await
            .map(|x| (fs_name.to_string(), x))
        } else {
            tracing::debug!("No fs_name. Returning MarkerNotFound error.");

            Err(EmfAgentError::MarkerNotFound)
        }
    });

    let snapshots: HashMap<String, Vec<Snapshot>> = try_join_all(xs).await?.into_iter().collect();

    tracing::debug!("snapshots: {:?}", snapshots);

    Ok(Some(snapshots))
}

#[tokio::main]
async fn main() -> Result<(), EmfAgentError> {
    emf_tracing::init();

    let mut x = interval(Duration::from_secs(10));

    let port = env::get_port("SNAPSHOT_AGENT_SNAPSHOT_SERVICE_PORT");

    let writer = create_filtered_writer(port);

    loop {
        x.tick().await;

        let x = list().await;

        let x = match x {
            Ok(x) => x,
            Err(e) => {
                tracing::debug!("Error calling list(): {:?}. Not processing snapshots.", e);
                continue;
            }
        };

        if let Some(x) = x {
            let _ = writer.send(x);
        }
    }
}
