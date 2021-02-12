// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::warp_drive::{Cache, Message};
use futures::{channel::mpsc, lock::Mutex, Stream, StreamExt};
use im::HashMap;
use std::sync::{
    atomic::{AtomicUsize, Ordering},
    Arc,
};
use warp::filters::sse::Event;

/// Global unique user id counter.
static NEXT_USER_ID: AtomicUsize = AtomicUsize::new(1);

pub type SharedUsers = Arc<Mutex<HashMap<usize, mpsc::UnboundedSender<Message>>>>;

pub async fn user_connected(
    state: SharedUsers,
    api_cache: Cache,
) -> impl Stream<Item = Result<Event, warp::Error>> {
    // Use a counter to assign a new unique ID for this user.
    let id = NEXT_USER_ID.fetch_add(1, Ordering::Relaxed);

    tracing::debug!("User connected {}", id);

    // Use an unbounded channel to handle buffering and flushing of messages
    // to the event source...
    let (tx, rx) = mpsc::unbounded();

    let _ = tx.unbounded_send(Message::Records(api_cache));

    // Save the sender in our list of connected users.
    state.lock().await.insert(id, tx);

    // Convert messages into Server-Sent Events and return resulting stream.
    rx.map(|msg| Ok(Event::default().data(serde_json::to_string(&msg).unwrap())))
}

/// Sends a message to each connected user
/// Any users for whom `unbounded_send` returns an error
/// will be dropped.
pub async fn send_message(msg: Message, state: SharedUsers) {
    tracing::debug!("Sending message {:?} to users {:?}", msg, state);

    let mut lock = state.lock().await;

    lock.retain(|id, tx| match tx.unbounded_send(msg.clone()) {
        Ok(()) => true,
        Err(_disconnected) => {
            tracing::debug!("user {} disconnected", id);

            false
        }
    });
}

pub async fn disconnect_all_users(state: SharedUsers) {
    tracing::info!("Flushing all users");

    state.lock().await.clear();
}
