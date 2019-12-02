// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future::try_join_all, stream::TryStreamExt};
use iml_ostpool::db::{self};
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::{OstPool, OstPoolAction};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();
    tracing::subscriber::set_global_default(subscriber).unwrap();

    let mut s = consume_data::<Vec<(OstPoolAction, OstPool)>>("rust_agent_ostpool_rx");

    while let Some((fqdn, pools)) = s.try_next().await? {
        tracing::debug!("Pools from {}: {:?}", fqdn, pools);

        let client = db::connect(fqdn).await?;

        let xs = pools.iter().map(|(state, pool)| {
            let client = client.clone();
            async move {
                tracing::debug!("{} pool {}.{}", state, pool.filesystem, pool.name);
                let fsid = client.fs2id(&pool.filesystem).await?;
                match state {
                    OstPoolAction::Initial => {
                        if client.exists(fsid, &pool.name).await? {
                            // @@
                            Ok(())
                        } else {
                            client.create(fsid, &pool.name).await?;
                            client.grow(fsid, &pool.name, &pool.osts).await
                        }
                    }
                    OstPoolAction::Add => {
                        if client.exists(fsid, &pool.name).await? {
                            Ok(())
                        } else {
                            client.create(fsid, &pool.name).await?;
                            client.grow(fsid, &pool.name, &pool.osts).await
                        }
                    }
                    OstPoolAction::Remove => {
                        if client.exists(fsid, &pool.name).await? {
                            client.shrink(fsid, &pool.name, &pool.osts).await?;
                            client.delete(fsid, &pool.name).await
                        } else {
                            Ok(())
                        }
                    }
                    OstPoolAction::Grow => {
                        if client.exists(fsid, &pool.name).await? {
                            client.grow(fsid, &pool.name, &pool.osts).await
                        } else {
                            tracing::warn!(
                                "Attempted to grow non-existant pool ({}.{})",
                                &pool.filesystem,
                                &pool.name
                            );
                            Ok(())
                        }
                    }
                    OstPoolAction::Shrink => {
                        if client.exists(fsid, &pool.name).await? {
                            client.shrink(fsid, &pool.name, &pool.osts).await
                        } else {
                            tracing::warn!(
                                "Attempted to shrink non-existant pool ({}.{})",
                                &pool.filesystem,
                                &pool.name
                            );
                            Ok(())
                        }
                    }
                }
            }
        });

        try_join_all(xs).await?;
    }

    Ok(())
}
