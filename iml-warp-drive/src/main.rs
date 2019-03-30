// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

// Long and nested future chains can quickly result in large generic types.
#![type_length_limit = "16777216"]

use futures::{
    future::{lazy, Future},
    sync::oneshot,
    Stream,
};
use iml_manager_env;
use iml_rabbit;
use iml_warp_drive::{
    locks::{self, create_locks_consumer, Locks},
    users,
};
use std::{
    collections::HashMap,
    ops::DerefMut,
    sync::{Arc, Mutex},
};
use warp::Filter;

type SharedLocks = Arc<Mutex<Locks>>;

fn main() {
    env_logger::init();

    // Keep track of all connected users, key is usize, value
    // is a event stream sender.
    let user_state: users::SharedUsers = Arc::new(Mutex::new(HashMap::new()));
    let lock_state: SharedLocks = Arc::new(Mutex::new(HashMap::new()));

    // Clone here to allow SSE route to get a ref.
    let user_state2 = user_state.clone();
    let lock_state2 = lock_state.clone();

    // Handle an error in locks by shutting down
    let (tx, rx) = oneshot::channel();

    let user_state3 = user_state.clone();
    let rx = rx.inspect(move |_| users::disconnect_all_users(&user_state3));

    tokio::run(lazy(move || {
        warp::spawn(
            iml_rabbit::connect_to_rabbit()
                .and_then(create_locks_consumer)
                .and_then(move |stream| {
                    log::debug!("Started consuming locks");

                    stream
                        .for_each(move |message| {
                            log::debug!("got message {:?}", std::str::from_utf8(&message.data));

                            let lock_change: locks::Changes =
                                serde_json::from_slice(&message.data).unwrap();

                            log::debug!("decoded message: {:?}", lock_change);

                            match lock_change {
                                locks::Changes::Locks(l) => {
                                    let mut hm = lock_state.lock().unwrap();
                                    hm.clear();
                                    hm.extend(l.result);

                                    users::send_message(
                                        serde_json::to_string(hm.deref_mut()).unwrap(),
                                        &user_state.clone(),
                                    );
                                }
                                locks::Changes::LockChange(l) => {
                                    let mut locks = lock_state.lock().unwrap();
                                    let locks = locks.deref_mut();

                                    locks::update_locks(locks, l);

                                    users::send_message(
                                        serde_json::to_string(&locks).unwrap(),
                                        &user_state.clone(),
                                    );
                                }
                            };

                            Ok(())
                        })
                        .map_err(failure::Error::from)
                })
                .map_err(|err| {
                    let _ = tx.send(());
                    eprintln!("An error occured: {}", err);
                }),
        );

        let users = warp::any().map(move || user_state2.clone());

        let locks = warp::any().map(move || lock_state2.clone());

        // GET -> messages stream
        let messaging = warp::get2().and(warp::sse()).and(users).and(locks).map(
            |sse: warp::sse::Sse, users: users::SharedUsers, locks: SharedLocks| {
                // reply using server-sent events
                let stream = users::user_connected(users, locks.lock().unwrap().deref_mut());
                sse.reply(warp::sse::keep(stream, None))
            },
        );

        let routes = messaging;

        log::info!("about to serve");

        let (_, fut) = warp::serve(routes)
            .bind_with_graceful_shutdown(iml_manager_env::get_warp_drive_addr(), rx);

        fut
    }));
}
