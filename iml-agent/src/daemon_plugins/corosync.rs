// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{DaemonPlugin, Output},
    high_availability::{get_crm_mon, get_local_nodeid},
};
use futures::{Future, FutureExt};
use std::{pin::Pin, time::Duration};

#[derive(Debug, Clone)]
struct Corosync;

pub fn create() -> impl DaemonPlugin {
    Corosync
}

impl DaemonPlugin for Corosync {
    fn deadline(&self) -> Duration {
        Duration::from_secs(10)
    }
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        self.update_session()
    }

    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        async move {
            let node_id = get_local_nodeid().await?;

            let cluster = get_crm_mon().await?;

            let x = match (node_id, cluster) {
                (Some(x), Some(y)) => Some((x, y)),
                _ => None,
            };

            let x = x.map(serde_json::to_value).transpose()?;

            Ok(x)
        }
        .boxed()
    }
}
