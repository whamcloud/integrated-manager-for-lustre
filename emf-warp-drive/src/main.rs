// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_postgres::{get_db_pool, sqlx};
use emf_warp_drive::{
    cache::{populate_from_db, SharedCache},
    error, listen, users,
};
use emf_wire_types::warp_drive::Cache;
use futures::{lock::Mutex, FutureExt, TryFutureExt};
use std::sync::Arc;
use warp::Filter;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pg_port = emf_manager_env::get_port("WARP_DRIVE_SERVICE_PG_PORT");

    let pool = get_db_pool(2, pg_port).await?;

    // Keep track of all connected users, key is `usize`, value
    // is a event stream sender.
    let user_state: users::SharedUsers = Arc::new(Mutex::new(im::hashmap! {}));

    let api_cache_state: SharedCache = Arc::new(Mutex::new(Cache::default()));

    // Clone here to allow SSE route to get a ref.
    let user_state2 = Arc::clone(&user_state);
    let api_cache_state2 = Arc::clone(&api_cache_state);

    // Handle an error in locks by shutting down
    let (exit, valve) = tokio_runtime_shutdown::shared_shutdown();

    let user_state3 = Arc::clone(&user_state);

    let api_cache_state3 = Arc::clone(&api_cache_state);

    tracing::info!("EMF warp drive starting");

    let listener = sqlx::postgres::PgListener::connect_with(&pool).await?;

    let fut = exit.wrap_fut(listen::handle_db_notifications(
        listener,
        api_cache_state,
        Arc::clone(&user_state),
    ));

    tokio::spawn(fut.map(|r: Result<(), error::EmfWarpDriveError>| match r {
        Ok(_) => tracing::info!("LISTEN / NOTIFY loop exited"),
        Err(e) => tracing::error!("Unhandled error {}", e),
    }));

    tracing::info!("Started listening to NOTIFY events");

    {
        populate_from_db(Arc::clone(&api_cache_state3), &pool).await?;
    }

    // GET -> messages stream
    let routes = warp::get()
        .and(warp::any().map(move || Arc::clone(&user_state2)))
        .and(warp::any().map(move || Arc::clone(&api_cache_state2)))
        .and_then(|users: users::SharedUsers, api_cache: SharedCache| {
            tracing::debug!("Inside user route");

            async move {
                // reply using server-sent events
                let stream = users::user_connected(users, api_cache.lock().await.clone()).await;

                Ok::<_, error::EmfWarpDriveError>(warp::sse::reply(
                    warp::sse::keep_alive().stream(stream),
                ))
            }
            .map_err(warp::reject::custom)
        })
        .with(warp::log("emf-warp-drive::api"));

    let port = emf_manager_env::get_port("WARP_DRIVE_SERVICE_PORT");

    tracing::info!("Listening on {}", port);

    let (_, fut) = warp::serve(routes).bind_with_graceful_shutdown(
        ([127, 0, 0, 1], port),
        tokio_runtime_shutdown::when_finished(&valve)
            .then(move |_| users::disconnect_all_users(user_state3)),
    );

    fut.await;

    Ok(())
}
