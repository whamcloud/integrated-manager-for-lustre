// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use emf_state_machine::{
    action_runner::{
        IncomingHostQueues, OutgoingHostQueues, INCOMING_HOST_QUEUES, OUTGOING_HOST_QUEUES,
    },
    Error,
};
use emf_wire_types::{ActionResult, Fqdn};
use std::{convert::Infallible, sync::Arc};
use warp::{http, Filter as _, Reply as _};

#[tokio::main]
async fn main() -> Result<(), Error> {
    emf_tracing::init();

    let get_actions = warp::get()
        .and(warp::header("x-client-fqdn"))
        .and(warp::header("x-instance-id"))
        .and(warp::any().map(move || Arc::clone(&OUTGOING_HOST_QUEUES)))
        .and_then(
            |fqdn: Fqdn, instance_id: String, outgoing_queues: OutgoingHostQueues| async move {
                let mut outgoing_queues = outgoing_queues.lock().await;

                let queue = outgoing_queues.entry(fqdn).or_insert(vec![]);

                let xs: Vec<_> = queue.drain(..).collect();

                Ok::<_, Infallible>(warp::reply::json(&xs))
            },
        );

    let ingest_responses = warp::post()
        .and(warp::header("x-client-fqdn"))
        .and(warp::header("x-instance-id"))
        .and(warp::body::json())
        .and(warp::any().map(move || Arc::clone(&INCOMING_HOST_QUEUES)))
        .and_then(
            |fqdn: Fqdn,
             instance_id: String,
             ActionResult { id, result },
             incoming_queues: IncomingHostQueues| async move {
                let mut incoming_queues = incoming_queues.lock().await;

                let queue = match incoming_queues.get_mut(&fqdn) {
                    Some(x) => x,
                    None => {
                        return Ok(warp::reply::with_status(
                            "FQDN not found",
                            http::StatusCode::BAD_REQUEST,
                        )
                        .into_response())
                    }
                };

                let tx = match queue.remove(&id) {
                    Some(x) => x,
                    None => {
                        return Ok(warp::reply::with_status(
                            "Action Id not found",
                            http::StatusCode::BAD_REQUEST,
                        )
                        .into_response())
                    }
                };

                let _ = tx.send(result);

                Ok::<_, Infallible>(http::StatusCode::ACCEPTED.into_response())
            },
        );

    let port = emf_manager_env::get_port("STATE_MACHINE_SERVICE_PORT");

    warp::serve(get_actions.or(ingest_responses))
        .run(([127, 0, 0, 1], port))
        .await;

    Ok(())
}
