// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_agent::{
    agent_error::EmfAgentError,
    env,
    high_availability::{get_crm_mon, get_local_nodeid},
    util::{create_filtered_writer, UnboundedSenderExt as _},
};
use std::time::Duration;
use tokio::time::interval;

#[tokio::main]
async fn main() -> Result<(), EmfAgentError> {
    emf_tracing::init();

    let mut x = interval(Duration::from_secs(5));

    let port = env::get_port("COROSYNC_AGENT_COROSYNC_SERVICE_PORT");
    let writer = create_filtered_writer(port)?;

    loop {
        x.tick().await;

        let node_id = get_local_nodeid().await?;

        let cluster = get_crm_mon().await?;

        if let Some(x) = node_id.zip(cluster) {
            let _ = writer.send_msg(x);
        }
    }
}
