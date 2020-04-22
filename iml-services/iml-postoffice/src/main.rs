// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryStreamExt;
use iml_service_queue::service_queue::consume_data;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let mut s = consume_data::<String>("rust_agent_postoffice_rx");

    while let Some((fqdn, s)) = s.try_next().await? {
        tracing::info!("Got some postoffice data from {:?}: {:?}", fqdn, s);
    }

    Ok(())
}
