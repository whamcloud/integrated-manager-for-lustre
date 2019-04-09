// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future::Future, lazy, stream::Stream};
use iml_services::{
    service_queue::consume_service_queue,
    services::action_runner::{
        data::{SessionToRpcs, Sessions, Shared},
        receiver::hande_agent_data,
        sender::{create_client_filter, sender},
    },
};
use iml_wire_types::PluginMessage;
use parking_lot::Mutex;
use std::{
    collections::HashMap,
    os::unix::{io::FromRawFd, net::UnixListener as NetUnixListener},
    sync::Arc,
};
use tokio::{net::UnixListener, reactor::Handle};
use warp::{self, Filter as _};

fn main() {
    env_logger::init();

    let (exit, valve) = tokio_runtime_shutdown::shared_shutdown();

    let sessions: Shared<Sessions> = Arc::new(Mutex::new(HashMap::new()));
    let rpcs: Shared<SessionToRpcs> = Arc::new(Mutex::new(HashMap::new()));

    tokio::run(lazy(move || {
        let addr = unsafe { NetUnixListener::from_raw_fd(3) };

        let listener = UnixListener::from_std(addr, &Handle::default())
            .expect("Unable to bind Unix Domain Socket fd");

        let log = warp::log("iml_action_runner::sender");

        let (fut, client_filter) = create_client_filter();

        tokio::spawn(fut);

        let routes = sender("", Arc::clone(&sessions), Arc::clone(&rpcs), client_filter)
            .map(|x| warp::reply::json(&x))
            .with(log);

        tokio::spawn(warp::serve(routes).serve_incoming(valve.wrap(listener.incoming())));

        iml_rabbit::connect_to_rabbit()
            .and_then(move |client| {
                exit.wrap(valve.wrap(consume_service_queue(
                    client.clone(),
                    "rust_agent_action_runner_rx",
                )))
                .for_each(move |m: PluginMessage| {
                    log::debug!("Incoming message from agent: {:?}", m);

                    hande_agent_data(client.clone(), m, &sessions, Arc::clone(&rpcs));

                    Ok(())
                })
            })
            .map_err(|e| log::error!("An error occured (agent side): {:?}", e))
    }));
}
