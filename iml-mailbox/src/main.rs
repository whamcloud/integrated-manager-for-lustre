// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Mailbox processor
//!
//! This crate allows N incoming writers to stream data to a single database table concurrently.
//!
//! Data has the requirement that it is line-delimited json so writes can be processed
//! concurrently

use futures::{Stream, StreamExt};
use iml_mailbox::ingest_data;
use iml_postgres::{get_db_pool, sqlx::PgPool};
use iml_tracing::tracing;
use std::pin::Pin;
use warp::Filter as _;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let pool = get_db_pool(5).await?;
    let db_pool_filter = warp::any().map(move || pool.clone());

    let addr = iml_manager_env::get_mailbox_addr();

    let mailbox = warp::path("mailbox");

    let post = warp::post()
        .and(mailbox)
        .and(warp::header::<String>("mailbox-message-name"))
        .and(iml_mailbox::line_stream())
        .and(db_pool_filter)
        .and_then(
            |task_name: String,
             s: Pin<Box<dyn Stream<Item = Result<String, warp::Rejection>> + Send>>,
             db_pool: PgPool| {
                async move {
                    tracing::debug!("Listening for task {}", &task_name);
                    s.filter_map(|l| async move { l.ok() })
                        .chunks(100)
                        .for_each_concurrent(10, |lines| {
                            let pool = db_pool.clone();
                            let task_name = task_name.clone();

                            async move {
                                if let Err(e) = ingest_data(pool, task_name, lines).await {
                                    tracing::warn!("Failed to process lines: {:?}", e);
                                }
                            }
                        })
                        .await;

                    Ok::<_, warp::reject::Rejection>(())
                }
            },
        )
        .map(|_| warp::reply::with_status(warp::reply(), warp::http::StatusCode::CREATED));

    let route = post.with(warp::log("mailbox"));

    tracing::info!("Starting on {:?}", addr);

    warp::serve(route).run(addr).await;

    Ok(())
}
