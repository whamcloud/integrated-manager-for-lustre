// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{cache::Cache, locks::Locks, Message};
use futures01::{
    future::{poll_fn, Future},
    sync::{mpsc, oneshot},
    Stream,
};
use parking_lot::Mutex;
use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicUsize, Ordering},
        Arc,
    },
};
use warp::sse::ServerSentEvent;

/// Global unique user id counter.
static NEXT_USER_ID: AtomicUsize = AtomicUsize::new(1);

pub type SharedUsers = Arc<Mutex<HashMap<usize, mpsc::UnboundedSender<Message>>>>;

pub fn user_connected(
    state: SharedUsers,
    locks: Locks,
    api_cache: Cache,
) -> impl Stream<Item = impl ServerSentEvent, Error = warp::Error> {
    // Use a counter to assign a new unique ID for this user.
    let id = NEXT_USER_ID.fetch_add(1, Ordering::Relaxed);

    log::debug!("User connected {}", id);

    // Use an unbounded channel to handle buffering and flushing of messages
    // to the event source...
    let (tx, rx) = mpsc::unbounded();

    let _ = tx.unbounded_send(Message::Records(api_cache));
    let _ = tx.unbounded_send(Message::Locks(locks));

    // Save the sender in our list of connected users.
    state.lock().insert(id, tx);

    // Make an extra clone of users list to give to our disconnection handler...
    let state2 = Arc::clone(&state);

    // Create channel to track disconnecting the receiver side of events.
    // This is little bit tricky.
    let (mut dtx, mut drx) = oneshot::channel::<()>();

    // When `drx` is dropped then `dtx` will be canceled.
    // We can track it to make sure when the user disconnects.
    warp::spawn(poll_fn(move || dtx.poll_cancel()).map(move |_| {
        user_disconnected(id, &state2);
    }));

    // Convert messages into Server-Sent Events and return resulting stream.
    rx.map(|msg| warp::sse::data(serde_json::to_string(&msg).unwrap()))
        .map_err(move |_| {
            // Keep `drx` alive until `rx` will be closed
            drx.close();
            unreachable!("unbounded rx never errors");
        })
}

pub fn send_message(msg: Message, state: SharedUsers) {
    log::debug!("Sending message {:?} to users {:?}", msg, state);

    for (_, tx) in state.lock().iter() {
        match tx.unbounded_send(msg.clone()) {
            Ok(()) => (),
            Err(_disconnected) => {
                // The tx is disconnected, our `user_disconnected` code
                // should be happening in another task, nothing more to
                // do here.
            }
        }
    }
}

pub fn disconnect_all_users(state: &SharedUsers) {
    log::info!("Flushing all users");

    state.lock().clear();
}

pub fn user_disconnected(id: usize, state: &SharedUsers) {
    log::debug!("user {} disconnected", id);

    // Stream ended, so remove from the user list
    state.lock().remove(&id);
}
