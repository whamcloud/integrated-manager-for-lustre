// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicUsize, Ordering},
        Arc, Mutex,
    },
};

use futures::{
    future::{poll_fn, Future},
    sync::{mpsc, oneshot},
    Stream,
};

use crate::locks::Locks;

use warp::sse::ServerSentEvent;

/// Our global unique user id counter.
static NEXT_USER_ID: AtomicUsize = AtomicUsize::new(1);

use crate::Message;

pub type SharedUsers = Arc<Mutex<HashMap<usize, mpsc::UnboundedSender<Message>>>>;

pub fn user_connected(
    state: SharedUsers,
    locks: &Locks,
) -> impl Stream<Item = impl ServerSentEvent, Error = warp::Error> {
    // Use a counter to assign a new unique ID for this user.
    let id = NEXT_USER_ID.fetch_add(1, Ordering::Relaxed);

    log::debug!("User connected {}", id);

    // Use an unbounded channel to handle buffering and flushing of messages
    // to the event source...
    let (tx, rx) = mpsc::unbounded();

    match tx.unbounded_send(Message::Data(serde_json::to_string(&locks).unwrap())) {
        Ok(()) => (),
        Err(_disconnected) => {
            // The tx is disconnected, our `user_disconnected` code
            // should be happening in another task, nothing more to
            // do here.
        }
    }

    // Make an extra clone of users list to give to our disconnection handler...
    let state2 = state.clone();

    // Save the sender in our list of connected users.
    state2.lock().unwrap().insert(id, tx);

    // Create channel to track disconnecting the receiver side of events.
    // This is little bit tricky.
    let (mut dtx, mut drx) = oneshot::channel::<()>();

    // When `drx` is dropped then `dtx` will be canceled.
    // We can track it to make sure when the user leaves chat.
    warp::spawn(poll_fn(move || dtx.poll_cancel()).map(move |_| {
        user_disconnected(id, &state2);
    }));

    // Convert messages into Server-Sent Events and return resulting stream.
    rx.map(|msg| match msg {
        Message::UserId(id) => (warp::sse::event("user"), warp::sse::data(id)).into_a(),
        Message::Data(reply) => warp::sse::data(reply).into_b(),
    })
    .map_err(move |_| {
        // Keep `drx` alive until `rx` will be closed
        drx.close();
        unreachable!("unbounded rx never errors");
    })
}

pub fn send_message(msg: String, state: &SharedUsers) {
    log::debug!("Sending message {:?} to users {:?}", msg, state);

    for (_, tx) in state.lock().unwrap().iter() {
        match tx.unbounded_send(Message::Data(msg.clone())) {
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
    log::debug!("Flushing all users");

    state.lock().unwrap().clear();
}

pub fn user_disconnected(id: usize, state: &SharedUsers) {
    log::debug!("user {} disconnected", id);

    // Stream closed up, so remove from the user list
    state.lock().unwrap().remove(&id);
}
