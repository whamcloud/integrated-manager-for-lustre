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

use futures::{Future as _, Stream as _};
use http::Response;
use hyper::Body;
use iml_mailbox::{LineStream, MailboxSenders};
use parking_lot::Mutex;
use std::{fs, path::PathBuf, sync::Arc};
use warp::Filter as _;

fn main() {
    env_logger::builder().default_format_timestamp(false).init();

    let addr = iml_manager_env::get_mailbox_addr();
    let mailbox_path = iml_manager_env::get_mailbox_path();

    type SharedMailboxSenders = Arc<Mutex<MailboxSenders>>;

    let shared_senders = Arc::new(Mutex::new(MailboxSenders::default()));
    let shared_senders_filter = warp::any().map(move || Arc::clone(&shared_senders));

    fs::create_dir_all(&mailbox_path).expect("could not create mailbox path");

    let mailbox = warp::path("mailbox");

    let mailbox_path2 = mailbox_path.clone();

    let get = warp::get2()
        .and(mailbox)
        .and(warp::path::param().map(move |x| [&mailbox_path2, &x].iter().collect()))
        .map(|address: PathBuf| {
            let stream = iml_fs::stream_file(address);

            let body = Body::wrap_stream(stream);

            Response::new(body)
        });

    let post = warp::post2()
        .and(mailbox)
        .and(shared_senders_filter)
        .and(
            warp::header::<PathBuf>("mailbox-message-name")
                .map(move |x| [&mailbox_path.clone(), &x].iter().collect()),
        )
        .and(iml_mailbox::line_stream())
        .and_then(
            |mailbox_senders: SharedMailboxSenders, address: PathBuf, s: Box<LineStream + Send>| {
                let tx = { mailbox_senders.lock().get(&address) };
                let tx = tx.unwrap_or_else(|| {
                    let (tx, fut) = { mailbox_senders.lock().create(address.clone()) };

                    let address2 = address.clone();

                    tokio::spawn(
                        fut.map(move |_| mailbox_senders.lock().remove(&address))
                            .map_err(move |e| {
                                log::error!(
                                    "Got an error writing to mailbox address {:?}: {:?}",
                                    &address2,
                                    e
                                )
                            }),
                    );

                    tx
                });

                s.for_each(move |l| {
                    log::debug!("Sending line {:?}", l);

                    tx.unbounded_send(l).map_err(warp::reject::custom)
                })
            },
        )
        .map(|_| warp::reply::with_status(warp::reply(), warp::http::StatusCode::CREATED));

    let routes = get.or(post).with(warp::log("mailbox"));

    log::info!("Starting on {:?}", addr);

    warp::serve(routes).run(addr);
}
