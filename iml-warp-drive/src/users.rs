// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{cache::Cache, locks::Locks, Message};
use futures::{
    channel::{mpsc, oneshot},
    future::poll_fn,
    lock::Mutex,
    Stream, StreamExt,
};
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

pub async fn user_connected(
    state: SharedUsers,
    locks: Locks,
    api_cache: Cache,
) -> impl Stream<Item = Result<impl ServerSentEvent, warp::Error>> {
    // Use a counter to assign a new unique ID for this user.
    let id = NEXT_USER_ID.fetch_add(1, Ordering::Relaxed);

    tracing::debug!("User connected {}", id);

    // Use an unbounded channel to handle buffering and flushing of messages
    // to the event source...
    let (tx, rx) = mpsc::unbounded();

    let _ = tx.unbounded_send(Message::Records(api_cache));
    let _ = tx.unbounded_send(Message::Locks(locks));

    // Save the sender in our list of connected users.
    state.lock().await.insert(id, tx);

    // Make an extra clone of users list to give to our disconnection handler...
    let state2 = Arc::clone(&state);

    // Create channel to track disconnecting the receiver side of events.
    // This is little bit tricky.
    let (mut dtx, mut drx) = oneshot::channel::<()>();

    // When `drx` is dropped then `dtx` will be canceled.
    // We can track it to make sure when the user disconnects.
    tokio::spawn(async move {
        poll_fn(move |cx| dtx.poll_cancel(cx)).await;
        drx.close();
        user_disconnected(id, &state2).await;
    });

    // Convert messages into Server-Sent Events and return resulting stream.
    rx.map(|msg| Ok(warp::sse::data(serde_json::to_string(&msg).unwrap())))
}

pub async fn send_message(msg: Message, state: SharedUsers) {
    tracing::debug!("Sending message {:?} to users {:?}", msg, state);

    let lock = state.lock().await;

    for (_, tx) in lock.iter() {
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

pub async fn disconnect_all_users(state: SharedUsers) {
    tracing::info!("Flushing all users");

    state.lock().await.clear();
}

pub async fn user_disconnected(id: usize, state: &SharedUsers) {
    tracing::debug!("user {} disconnected", id);

    // Stream ended, so remove from the user list
    state.lock().await.remove(&id);
}
