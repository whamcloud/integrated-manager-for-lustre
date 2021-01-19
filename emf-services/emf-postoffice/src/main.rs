// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_service_queue::service_queue::consume_data;
use futures::TryStreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pool = emf_rabbit::connect_to_rabbit(1);

    let conn = emf_rabbit::get_conn(pool).await?;

    let ch = emf_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<String>(&ch, "rust_agent_postoffice_rx");

    while let Some((fqdn, s)) = s.try_next().await? {
        tracing::info!("Got some postoffice data from {:?}: {:?}", fqdn, s);
    }

    Ok(())
}
