// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Mailbox processor
//!
//! This crate allows N incoming writers to stream data to a known
//! file-backed address concurrently.
//!
//! Data has the requirement that is line-delimited so writes can be processed
//! concurrently

use futures::{lock::Mutex, Stream, TryStreamExt};
use iml_mailbox::{Errors, MailboxSenders};
use std::{fs, path::PathBuf, pin::Pin, sync::Arc};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::Filter as _;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let addr = iml_manager_env::get_mailbox_addr();
    let mailbox_path = iml_manager_env::get_mailbox_path();

    type SharedMailboxSenders = Arc<Mutex<MailboxSenders>>;

    let shared_senders = Arc::new(Mutex::new(MailboxSenders::default()));
    let shared_senders_filter = warp::any().map(move || Arc::clone(&shared_senders));

    fs::create_dir_all(&mailbox_path).expect("could not create mailbox path");

    let mailbox = warp::path("mailbox");

    let post = warp::post()
        .and(mailbox)
        .and(shared_senders_filter)
        .and(
            warp::header::<PathBuf>("mailbox-message-name")
                .map(move |x| [&mailbox_path.clone(), &x].iter().collect()),
        )
        .and(iml_mailbox::line_stream())
        .and_then(
            |mailbox_senders: SharedMailboxSenders,
             address: PathBuf,
             mut s: Pin<Box<dyn Stream<Item = Result<String, warp::Rejection>> + Send>>| {
                async move {
                    let tx = {
                        let mut lock = mailbox_senders.lock().await;

                        lock.get(&address)
                    };

                    let tx = match tx {
                        Some(tx) => tx,
                        None => {
                            let (tx, fut) = {
                                let mut lock = mailbox_senders.lock().await;
                                lock.create(address.clone())
                            };

                            let address2 = address.clone();

                            tokio::spawn(
                                async move {
                                    fut.await.unwrap_or_else(|e| {
                                        tracing::error!(
                                            "Got an error writing to mailbox address {:?}: {:?}",
                                            &address2,
                                            e
                                        )
                                    });

                                    let mut lock = mailbox_senders.lock().await;
                                    lock.remove(&address);
                                }
                            );

                            tx
                        }
                    };


                    while let Some(l) = s.try_next().await? {
                        tracing::debug!("Sending line {:?}", l);

                        tx.unbounded_send(l).map_err(Errors::TrySendError).map_err(warp::reject::custom)?
                    }

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
