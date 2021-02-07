// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::Fqdn;
use tokio::sync::mpsc;
use warp::{reply::WithStatus, Filter, Reply};

pub type Incoming<T> = (Fqdn, T);

/// Creates a warp `Filter` that will handle incoming POSTs from other services.
/// It should be spawned as a new task with tokio.
// A Rx handle is also returned. It should be consumed to work with `Incoming` data.
pub fn create_service_consumer<T: Send + serde::de::DeserializeOwned>() -> (
    impl Filter<Extract = (WithStatus<impl Reply>,), Error = warp::Rejection> + Clone,
    mpsc::UnboundedReceiver<Incoming<T>>,
) {
    let (tx, rx) = mpsc::unbounded_channel::<Incoming<T>>();

    let x = warp::post()
        .and(warp::body::json())
        .map(move |x: Incoming<T>| {
            let x = match tx.clone().send(x) {
                Ok(_) => warp::http::StatusCode::ACCEPTED,
                Err(_) => warp::http::StatusCode::INTERNAL_SERVER_ERROR,
            };

            warp::reply::with_status(warp::reply(), x)
        });

    (x, rx)
}

/// Spawns a new server that listens for incoming POSTs
/// from other services on the given port.
pub fn spawn_service_consumer<T: Send + serde::de::DeserializeOwned + 'static>(
    port: u16,
) -> mpsc::UnboundedReceiver<Incoming<T>> {
    let (x, rx) = create_service_consumer();

    let server = warp::serve(x).run(([127, 0, 0, 1], port));

    tokio::spawn(server);

    rx
}
