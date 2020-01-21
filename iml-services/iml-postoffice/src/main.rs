// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryStreamExt;
use iml_service_queue::service_queue::consume_data;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let mut s = consume_data::<String>("rust_agent_postoffice_rx");

    while let Some((fqdn, s)) = s.try_next().await? {
        tracing::info!("Got some postoffice data from {:?}: {:?}", fqdn, s);
    }

    Ok(())
}
