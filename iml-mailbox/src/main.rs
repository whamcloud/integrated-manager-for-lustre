// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Mailbox processor
//!
//! This crate allows N incoming writers to stream data to a known
//! file-backed address concurrently.
//!
//! Data has the requirement that is line-delimited so writes can be processed
//! concurrently

use futures::{lock::Mutex, Stream, TryFutureExt, TryStreamExt};
use iml_mailbox::{Incoming, MailboxError, MailboxSenders};
use std::{pin::Pin, sync::Arc};
use warp::Filter as _;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let addr = iml_manager_env::get_mailbox_addr();

    type SharedMailboxSenders = Arc<Mutex<MailboxSenders>>;

    let shared_senders = Arc::new(Mutex::new(MailboxSenders::default()));
    let shared_senders_filter = warp::any().map(move || Arc::clone(&shared_senders));

    //let pool = iml_orm::pool()?;

    let mailbox = warp::path("mailbox");

    let post = warp::post()
        .and(mailbox)
        .and(shared_senders_filter)
        .and(warp::header::<String>("mailbox-message-name"))
        .and(iml_mailbox::line_stream())
        .and_then(
            |mailbox_senders: SharedMailboxSenders,
             task_name: String,
             mut s: Pin<Box<dyn Stream<Item = Result<String, warp::Rejection>> + Send>>| {
                async move {
                    let tx = {
                        let mut lock = mailbox_senders.lock().await;

                        lock.get(&task_name)
                    };

                    let tx = match tx {
                        Some(tx) => tx,
                        None => {
                            let (tx, fut) = {
                                let mut lock = mailbox_senders.lock().await;
                                lock.create(task_name.clone())
                            };

                            let task_name2 = task_name.clone();

                            tokio::spawn(
                                async move {
                                    fut.await.unwrap_or_else(|e| {
                                        tracing::error!(
                                            "Got an error writing to mailbox {:?}: {:?}",
                                            &task_name2,
                                            e
                                        )
                                    });

                                    let mut lock = mailbox_senders.lock().await;
                                    lock.remove(&task_name);
                                }
                            );

                            tx
                        }
                    };


                    while let Some(l) = s.try_next().await? {
                        tracing::debug!("Sending line {:?}", l);

                        tx.unbounded_send(Incoming::Line(l)).map_err(MailboxError::TrySendError).map_err(warp::reject::custom)?
                    }


                    let (eof, rx) = Incoming::create_eof();

                    tx.unbounded_send(eof).map_err(MailboxError::TrySendError).map_err(warp::reject::custom)?;

                    let _ = rx.map_err(|e| tracing::warn!("Error waiting for flush {:?}", e)).await;

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
