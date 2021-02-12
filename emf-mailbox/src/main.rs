// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Mailbox processor
//!
//! This crate allows N incoming writers to stream data to a single database table concurrently.
//!
//! Data has the requirement that it is line-delimited json so writes can be processed
//! concurrently

use emf_mailbox::ingest_data;
use emf_manager_env::get_pool_limit;
use emf_postgres::get_db_pool;
use emf_tracing::tracing;
use futures::{Stream, StreamExt};
use lazy_static::lazy_static;
use sqlx::postgres::PgPool;
use std::pin::Pin;
use warp::Filter as _;

// Default pool limit if not overridden by POOL_LIMIT
lazy_static! {
    static ref POOL_LIMIT: u32 = get_pool_limit().unwrap_or(8);
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pool = get_db_pool(
        *POOL_LIMIT,
        emf_manager_env::get_port("MAILBOX_SERVICE_PORT"),
    )
    .await?;
    let db_pool_filter = warp::any().map(move || pool.clone());

    let addr = emf_manager_env::get_mailbox_addr();

    let mailbox = warp::path("mailbox");

    let post = warp::post()
        .and(mailbox)
        .and(warp::header::<String>("mailbox-message-name"))
        .and(emf_mailbox::line_stream())
        .and(db_pool_filter)
        .and_then(
            |task_name: String,
             s: Pin<Box<dyn Stream<Item = Result<String, warp::Rejection>> + Send>>,
             db_pool: PgPool| {
                async move {
                    tracing::debug!("Listening for task {}", &task_name);

                    s.filter_map(|l| async move { l.ok() })
                        .chunks(1000)
                        .for_each_concurrent(*POOL_LIMIT as usize, |lines| {
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
