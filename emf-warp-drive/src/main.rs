// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_manager_client::get_client;
use emf_postgres::get_db_pool;
use emf_warp_drive::{
    cache::{populate_from_api, populate_from_db, SharedCache},
    error, listen,
    locks::{self, create_locks_consumer, Locks},
    users,
};
use emf_wire_types::warp_drive::{Cache, Message};
use futures::{lock::Mutex, FutureExt, TryFutureExt, TryStreamExt};
use std::sync::Arc;
use warp::Filter;

type SharedLocks = Arc<Mutex<Locks>>;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    // Keep track of all connected users, key is `usize`, value
    // is a event stream sender.
    let user_state: users::SharedUsers = Arc::new(Mutex::new(im::hashmap! {}));

    let lock_state: SharedLocks = Arc::new(Mutex::new(im::hashmap! {}));

    let api_cache_state: SharedCache = Arc::new(Mutex::new(Cache::default()));

    // Clone here to allow SSE route to get a ref.
    let user_state2 = Arc::clone(&user_state);
    let lock_state2 = Arc::clone(&lock_state);
    let api_cache_state2 = Arc::clone(&api_cache_state);

    // Handle an error in locks by shutting down
    let (exit, valve) = tokio_runtime_shutdown::shared_shutdown();

    let user_state3 = Arc::clone(&user_state);

    let api_cache_state3 = Arc::clone(&api_cache_state);

    let api_client = get_client()?;

    tracing::info!("EMF warp drive starting");

    populate_from_api(Arc::clone(&api_cache_state)).await?;

    let (db_client, conn) = emf_postgres::connect().await?;
    let shared_client = emf_postgres::shared_client(db_client);

    let c2 = Arc::clone(&shared_client);

    let notify_stream = emf_postgres::NotifyStream(conn);

    let notify_stream = valve.wrap(notify_stream);

    let notify_stream = exit.wrap_fut(listen::handle_db_notifications(
        notify_stream,
        Arc::clone(&c2),
        api_client,
        api_cache_state,
        Arc::clone(&user_state),
    ));

    tokio::spawn(
        notify_stream.map(|r: Result<(), error::EmfWarpDriveError>| match r {
            Ok(_) => tracing::info!("LISTEN / NOTIFY loop exited"),
            Err(e) => tracing::error!("Unhandled error {}", e),
        }),
    );

    {
        let c = shared_client.lock().await;

        c.simple_query("LISTEN table_update").await?;
    }

    tracing::info!("Started listening to NOTIFY events");

    {
        let pool = get_db_pool(2).await?;

        populate_from_db(Arc::clone(&api_cache_state3), &pool).await?;
    }

    let pool = emf_rabbit::connect_to_rabbit(1);

    let conn = emf_rabbit::get_conn(pool).await?;

    let ch = emf_rabbit::create_channel(&conn).await?;

    let locks_consumer_stream = create_locks_consumer(&ch).await?;

    let mut s = valve.wrap(locks_consumer_stream);

    tokio::spawn(
        async move {
            while let Some(message) = s.try_next().map_err(error::EmfWarpDriveError::from).await? {
                tracing::debug!("got message {:?}", std::str::from_utf8(&message.data));

                let lock_change: locks::Changes = serde_json::from_slice(&message.data)?;

                tracing::debug!("decoded message: {:?}", lock_change);

                match lock_change {
                    locks::Changes::Locks(l) => {
                        let mut hm = lock_state.lock().await;
                        hm.clear();
                        hm.extend(l.result);

                        users::send_message(Message::Locks(hm.clone()), Arc::clone(&user_state))
                            .await;
                    }
                    locks::Changes::LockChange(l) => {
                        {
                            let mut lock = lock_state.lock().await;
                            locks::update_locks(&mut lock, l);
                        }

                        let data = {
                            let locks = lock_state.lock().await;
                            locks.clone()
                        };

                        users::send_message(Message::Locks(data), Arc::clone(&user_state)).await;
                    }
                };
            }

            Ok(())
        }
        .map_err(exit.trigger_fn())
        .map(|r: Result<(), error::EmfWarpDriveError>| match r {
            Ok(_) => tracing::info!("Rabbit client stream exited"),
            Err(e) => tracing::error!("Unhandled error {}", e),
        }),
    );

    // GET -> messages stream
    let routes = warp::get()
        .and(warp::any().map(move || Arc::clone(&user_state2)))
        .and(warp::any().map(move || Arc::clone(&lock_state2)))
        .and(warp::any().map(move || Arc::clone(&api_cache_state2)))
        .and_then(
            |users: users::SharedUsers, locks: SharedLocks, api_cache: SharedCache| {
                tracing::debug!("Inside user route");

                async move {
                    // reply using server-sent events
                    let stream = users::user_connected(
                        users,
                        locks.lock().await.clone(),
                        api_cache.lock().await.clone(),
                    )
                    .await;

                    Ok::<_, error::EmfWarpDriveError>(warp::sse::reply(
                        warp::sse::keep_alive().stream(stream),
                    ))
                }
                .map_err(warp::reject::custom)
            },
        )
        .with(warp::log("emf-warp-drive::api"));

    let addr = emf_manager_env::get_warp_drive_addr();

    tracing::info!("Listening on {}", addr);

    let (_, fut) = warp::serve(routes).bind_with_graceful_shutdown(
        addr,
        tokio_runtime_shutdown::when_finished(&valve)
            .then(move |_| users::disconnect_all_users(user_state3)),
    );

    fut.await;

    Ok(())
}
