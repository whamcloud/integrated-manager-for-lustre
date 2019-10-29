// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::request::Request;
use futures01::future::Future;
use iml_rabbit::{
    basic_consume, basic_publish, bind_queue, create_channel, declare_transient_exchange,
    declare_transient_queue, purge_queue, TcpChannel, TcpChannelFuture, TcpClient,
};
use iml_wire_types::{LockAction, LockChange, ToCompositeId};
use lapin_futures::{channel::BasicConsumeOptions, queue::Queue};
use std::collections::{HashMap, HashSet};

/// Declares the exchange for rpc comms
fn declare_rpc_exchange(c: TcpChannel) -> impl TcpChannelFuture {
    declare_transient_exchange(c, "rpc", "topic")
}

/// Declares the queue used for locks
fn declare_locks_queue(
    c: TcpChannel,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> {
    declare_transient_queue(c, "locks")
}

/// Creates a consumer for the locks queue.
/// This fn will first purge the locks queue
/// and then make a one-off request to get
/// all locks currently held in the job-scheduler.
///
/// This is expected to be called once during startup.
pub fn create_locks_consumer(
    client: TcpClient,
) -> impl Future<Item = lapin_futures::consumer::Consumer<tokio::net::TcpStream>, Error = failure::Error>
{
    create_channel(client)
        .and_then(declare_rpc_exchange)
        .and_then(declare_locks_queue)
        .and_then(|(c, q)| bind_queue(c, "rpc", "locks", "locks").map(move |c2| (c2, q)))
        .and_then(|(c, q)| purge_queue(c, "locks").map(move |c2| (c2, q)))
        .and_then(|(c, q)| {
            basic_publish(
                c,
                "rpc",
                "JobSchedulerRpc.requests",
                Request::new("get_locks", "locks"),
            )
            .map(move |c2| (c2, q))
        })
        .and_then(|(c, q)| {
            basic_consume(
                c,
                q,
                "locks",
                Some(BasicConsumeOptions {
                    no_ack: true,
                    exclusive: true,
                    ..BasicConsumeOptions::default()
                }),
            )
        })
        .map_err(failure::Error::from)
}

/// Need to wrap `LockChange` with this, because it's how
/// the RPC layer in IML returns RPC calls.
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq)]
pub struct Response {
    pub exception: Option<String>,
    pub result: Locks,
    pub request_id: String,
}

/// Variants that can appear over the locks queue
/// Currently can either reset the `Locks` state as
/// a whole, or add / remove locks from it.
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq)]
#[serde(untagged)]
pub enum Changes {
    Locks(Response),
    LockChange(LockChange),
}

/// The current state of locks based on data from the locks queue
pub type Locks = HashMap<String, HashSet<LockChange>>;

/// Add a new lock to `Locks`
pub fn add_lock(locks: &mut Locks, lock_change: LockChange) {
    locks
        .entry(lock_change.composite_id().to_string())
        .or_insert_with(HashSet::new)
        .insert(lock_change);

    log::debug!("(add) locks is now {:?}", locks);
}

/// Remove a lock from `Locks` if it exists
pub fn remove_lock(locks: &mut Locks, lock_change: &LockChange) {
    locks
        .entry(lock_change.composite_id().to_string())
        .and_modify(|xs: &mut HashSet<LockChange>| xs.retain(|x| x.uuid != lock_change.uuid));

    locks.retain(|_, xs| !xs.is_empty());

    log::debug!("(remove) locks is now {:?}", locks);
}

/// Update `Locks` based on a change. Will either attempt an add or remove.
pub fn update_locks(locks: &mut Locks, lock_change: LockChange) {
    match lock_change.action {
        LockAction::Add => add_lock(locks, lock_change),
        LockAction::Remove => remove_lock(locks, &lock_change),
    };
}
