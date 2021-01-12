// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Report processor
//!
//! This crate allows N incoming writers to stream data to a known
//! file-backed address concurrently.
//!
//! Data has the requirement that is line-delimited so writes can be processed
//! concurrently

use emf_report::{Errors, Incoming, ReportSenders};
use futures::{lock::Mutex, Stream, TryFutureExt, TryStreamExt};
use std::{fs, path::PathBuf, pin::Pin, sync::Arc};
use warp::Filter as _;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let addr = emf_manager_env::get_report_addr();
    let report_path = emf_manager_env::get_report_path();

    type SharedReportSenders = Arc<Mutex<ReportSenders>>;

    let shared_senders = Arc::new(Mutex::new(ReportSenders::default()));
    let shared_senders_filter = warp::any().map(move || Arc::clone(&shared_senders));

    fs::create_dir_all(&report_path).expect("could not create report path");

    let report = warp::path("report");

    let post = warp::post()
        .and(report)
        .and(shared_senders_filter)
        .and(
            warp::header::<PathBuf>("report-message-name")
                .map(move |x| [&report_path.clone(), &x].iter().collect()),
        )
        .and(emf_report::line_stream())
        .and_then(
            |report_senders: SharedReportSenders,
             address: PathBuf,
             mut s: Pin<Box<dyn Stream<Item = Result<String, warp::Rejection>> + Send>>| {
                async move {
                    let tx = {
                        let mut lock = report_senders.lock().await;

                        lock.get(&address)
                    };

                    let tx = match tx {
                        Some(tx) => tx,
                        None => {
                            let (tx, fut) = {
                                let mut lock = report_senders.lock().await;
                                lock.create(address.clone())
                            };

                            let address2 = address.clone();

                            tokio::spawn(
                                async move {
                                    fut.await.unwrap_or_else(|e| {
                                        tracing::error!(
                                            "Got an error writing to report address {:?}: {:?}",
                                            &address2,
                                            e
                                        )
                                    });

                                    let mut lock = report_senders.lock().await;
                                    lock.remove(&address);
                                }
                            );

                            tx
                        }
                    };


                    while let Some(l) = s.try_next().await? {
                        tracing::debug!("Sending line {:?}", l);

                        tx.unbounded_send(Incoming::Line(l)).map_err(Errors::TrySendError).map_err(warp::reject::custom)?
                    }


                    let (eof, rx) = Incoming::create_eof();

                    tx.unbounded_send(eof).map_err(Errors::TrySendError).map_err(warp::reject::custom)?;

                    let _ = rx.map_err(|e| tracing::warn!("Error waiting for flush {:?}", e)).await;

                    Ok::<_, warp::reject::Rejection>(())
                }
            },
        )
        .map(|_| warp::reply::with_status(warp::reply(), warp::http::StatusCode::CREATED));

    let route = post.with(warp::log("report"));

    tracing::info!("Starting on {:?}", addr);

    warp::serve(route).run(addr).await;

    Ok(())
}
