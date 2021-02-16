// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::Fqdn;
use tokio::sync::mpsc;
use tokio_stream::wrappers::UnboundedReceiverStream;
use uuid::Uuid;
use warp::{
    http::{
        header::{ETAG, IF_NONE_MATCH},
        StatusCode,
    },
    Filter, Reply,
};

pub type Incoming<T> = (Fqdn, T);

/// Creates a warp `Filter` that will handle incoming POSTs from other services.
/// It should be spawned as a new task with tokio.
// A Rx handle is also returned. It should be consumed to work with `Incoming` data.
pub fn create_service_consumer<T: Send + serde::de::DeserializeOwned>() -> (
    impl Filter<Extract = (StatusCode,), Error = warp::Rejection> + Clone,
    UnboundedReceiverStream<Incoming<T>>,
) {
    let (tx, rx) = mpsc::unbounded_channel::<Incoming<T>>();

    let x = warp::post()
        .and(warp::body::json())
        .map(move |x: Incoming<T>| match tx.clone().send(x) {
            Ok(_) => StatusCode::ACCEPTED,
            Err(_) => StatusCode::INTERNAL_SERVER_ERROR,
        });

    (x, UnboundedReceiverStream::new(rx))
}

/// Creates a warp `Filter` to verify if the service instance has changed.
fn create_service_identifier(
) -> impl Filter<Extract = (impl Reply,), Error = warp::Rejection> + Clone {
    let instance_id = Uuid::new_v4();

    warp::get()
        .and(warp::header(IF_NONE_MATCH.as_str()))
        .and(warp::any().map(move || instance_id.to_string()))
        .map(|tag: String, x: String| {
            if tag == x {
                StatusCode::NOT_MODIFIED.into_response()
            } else {
                warp::reply::with_header(StatusCode::OK, ETAG, x).into_response()
            }
        })
}

/// Spawns a new server that listens for incoming POSTs
/// from other services on the given port.
pub fn spawn_service_consumer<T: Send + serde::de::DeserializeOwned + 'static>(
    port: u16,
) -> UnboundedReceiverStream<Incoming<T>> {
    let (consumer, rx) = create_service_consumer();
    let identifier = create_service_identifier();

    let server = warp::serve(consumer.or(identifier)).run(([127, 0, 0, 1], port));

    tokio::spawn(server);

    rx
}
