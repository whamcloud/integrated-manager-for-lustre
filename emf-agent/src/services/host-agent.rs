// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Host agent service
//!
//!

use emf_agent::{
    agent_error::EmfAgentError,
    env,
    util::{create_filtered_writer, BOOT_TIME, MACHINE_ID},
};
use std::{ops::Deref, time::Duration};
use tokio::time::interval;

#[tokio::main]
async fn main() -> Result<(), EmfAgentError> {
    emf_tracing::init();

    let mut x = interval(Duration::from_secs(5));

    let port = env::get_port("HOST_AGENT_HOST_SERVICE_PORT");

    let writer = create_filtered_writer(port);

    loop {
        x.tick().await;

        let _ = writer.send((MACHINE_ID.to_string(), BOOT_TIME.deref()));
    }
}
