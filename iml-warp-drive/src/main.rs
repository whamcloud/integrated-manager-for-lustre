// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    future::{self, lazy, Future, IntoFuture},
    sync::oneshot,
    Stream,
};
use iml_manager_client::get_client;
use iml_manager_env;
use iml_warp_drive::{
    cache::{self, populate_from_api, populate_from_db, Cache, SharedCache},
    listen,
    locks::{self, create_locks_consumer, Locks},
    users, Message,
};
use parking_lot::Mutex;
use std::{collections::HashMap, sync::Arc};
use warp::Filter;

type SharedLocks = Arc<Mutex<Locks>>;

fn main() {
    env_logger::builder().default_format_timestamp(false).init();

    // Keep track of all connected users, key is `usize`, value
    // is a event stream sender.
    let user_state: users::SharedUsers = Arc::new(Mutex::new(HashMap::new()));

    let lock_state: SharedLocks = Arc::new(Mutex::new(HashMap::new()));

    let api_cache_state: SharedCache = Arc::new(Mutex::new(Cache::default()));

    // Clone here to allow SSE route to get a ref.
    let user_state2 = Arc::clone(&user_state);
    let lock_state2 = Arc::clone(&lock_state);
    let api_cache_state2 = Arc::clone(&api_cache_state);

    // Handle an error in locks by shutting down
    let (tx, rx) = oneshot::channel();

    let user_state3 = Arc::clone(&user_state);
    let rx = rx.inspect(move |_| users::disconnect_all_users(&user_state3));

    let user_state4 = Arc::clone(&user_state);

    let api_cache_state3 = Arc::clone(&api_cache_state);

    let api_client = get_client().unwrap();

    tokio::run(lazy(move || {
        warp::spawn(
            populate_from_api(Arc::clone(&api_cache_state))
                .map_err(|e| -> failure::Error { e.into() })
                .and_then(|_| iml_postgres::connect().from_err())
                .map(|(client, conn)| {
                    (
                        iml_postgres::shared_client(client),
                        iml_postgres::NotifyStream(conn),
                    )
                })
                .and_then(move |(client, stream)| {
                    let c2 = Arc::clone(&client);

                    log::debug!("Cache state {:?}", api_cache_state);

                    warp::spawn(
                        stream
                        .from_err()
                            .for_each(move |msg| -> Box<Future<Item = (), Error = failure::Error> + Send> {
                                let c3 = &c2;

                                let api_client = api_client.clone();
                                let api_cache_state = Arc::clone(&api_cache_state);
                                let user_state4 = Arc::clone(&user_state4);

                                match msg {
                                    iml_postgres::AsyncMessage::Notification(n) => {
                                        if n.channel() == "table_update" {
                                            let fut = listen::into_db_record(n.payload())
                                                .into_future()
                                                .from_err()
                                                .and_then(|r| {
                                                    cache::db_record_to_change_record(r, api_client)
                                                        .from_err()
                                                })
                                                .map(move |record_change| {
                                                    match record_change.clone() {
                                                        cache::RecordChange::Delete(r) => {
                                                            let removed = api_cache_state.lock().remove_record(&r);

                                                            if removed {
                                                                users::send_message(Message::RecordChange(record_change), Arc::clone(&user_state4));
                                                            }
                                                        }
                                                        cache::RecordChange::Update(r) => {
                                                            api_cache_state.lock().insert_record(r);

                                                            users::send_message(Message::RecordChange(record_change), Arc::clone(&user_state4));
                                                        }
                                                    };
                                                });

                                                Box::new(fut)
                                        } else {
                                            log::warn!("unknown channel: {}", n.channel());

                                            Box::new(future::ok(()))
                                        }
                                    }
                                    iml_postgres::AsyncMessage::Notice(err) => {
                                        Box::new(future::err(err).from_err())
                                    }
                                    _ => unreachable!()
                                }
                            })
                            .map_err(|e| log::error!("{}", e)),
                    );

                    let fut = {
                        let c = Arc::clone(&client);
                        let mut c = c.lock();

                        c.simple_query("LISTEN table_update")
                        .for_each(|_| Ok(()))
                        .from_err()
                    };

                    fut.and_then(move |_| {
                        populate_from_db(Arc::clone(&api_cache_state3), client)
                        .from_err()
                    })
                })
                .inspect(|_| log::info!("Started listening to NOTIFY events"))
                .map_err(|e| log::error!("{}", e)),
        );

        warp::spawn(
            iml_rabbit::connect_to_rabbit()
                .and_then(create_locks_consumer)
                .and_then(move |stream| {
                    log::info!("Started consuming locks");

                    stream
                        .for_each(move |message| {
                            log::debug!("got message {:?}", std::str::from_utf8(&message.data));

                            let lock_change: locks::Changes =
                                serde_json::from_slice(&message.data).unwrap();

                            log::debug!("decoded message: {:?}", lock_change);

                            match lock_change {
                                locks::Changes::Locks(l) => {
                                    let mut hm = lock_state.lock();
                                    hm.clear();
                                    hm.extend(l.result);

                                    users::send_message(
                                        Message::Locks(hm.clone()),
                                        Arc::clone(&user_state),
                                    );
                                }
                                locks::Changes::LockChange(l) => {
                                    locks::update_locks(&mut lock_state.lock(), l);

                                    let data = {
                                        let locks = lock_state.lock();
                                        locks.clone()
                                    };

                                    users::send_message(
                                        Message::Locks(data),
                                        Arc::clone(&user_state),
                                    );
                                }
                            };

                            Ok(())
                        })
                        .from_err()
                })
                .map_err(|err| {
                    let _ = tx.send(());
                    eprintln!("An error occurred: {}", err);
                }),
        );

        let users = warp::any().map(move || Arc::clone(&user_state2));

        let locks = warp::any().map(move || Arc::clone(&lock_state2));

        let api_cache = warp::any().map(move || Arc::clone(&api_cache_state2));

        // GET -> messages stream
        let routes = warp::get2()
            .and(warp::sse())
            .and(users)
            .and(locks)
            .and(api_cache)
            .map(
                |sse: warp::sse::Sse,
                 users: users::SharedUsers,
                 locks: SharedLocks,
                 api_cache: SharedCache| {
                    // reply using server-sent events
                    let stream = users::user_connected(
                        users,
                        locks.lock().clone(),
                        api_cache.lock().clone(),
                    );
                    sse.reply(warp::sse::keep_alive().stream(stream))
                },
            )
            .with(warp::log("iml-warp-drive::api"));

        log::info!("IML warp drive starting");

        let (_, fut) = warp::serve(routes)
            .bind_with_graceful_shutdown(iml_manager_env::get_warp_drive_addr(), rx);

        fut
    }));
}
