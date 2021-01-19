// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::session::SharedSessions;
use emf_wire_types::Fqdn;
use futures::{channel::oneshot, lock::Mutex};
use std::{
    collections::{HashMap, VecDeque},
    sync::Arc,
};

/// References an active agent on a remote host.
///
/// Contains references to any active sessions on the remote host,
/// and maintains a `VecDeque` of outgoing messages to send to the remote host.
#[derive(Debug)]
pub struct Host {
    pub fqdn: Fqdn,
    pub client_start_time: String,
    pub stop_reading: Option<oneshot::Sender<Vec<Vec<u8>>>>,
    pub queue: Arc<Mutex<VecDeque<Vec<u8>>>>,
    pub sessions: SharedSessions,
}

impl Host {
    pub fn new(fqdn: Fqdn, client_start_time: String) -> Self {
        Self {
            fqdn,
            client_start_time,
            stop_reading: None,
            queue: Arc::new(Mutex::new(VecDeque::new())),
            sessions: Arc::new(Mutex::new(HashMap::new())),
        }
    }
    pub fn stop(&mut self) {
        self.stop_reading.take().map(|h| h.send(vec![]));
    }
}

pub type Hosts = HashMap<Fqdn, Host>;
pub type SharedHosts = Arc<Mutex<Hosts>>;

pub fn shared_hosts() -> SharedHosts {
    Arc::new(Mutex::new(HashMap::new()))
}

/// Gets or inserts a new host cooresponding to the given fqdn
pub fn get_or_insert(hosts: &mut Hosts, fqdn: Fqdn, client_start_time: String) -> &mut Host {
    hosts.entry(fqdn.clone()).or_insert_with(|| {
        tracing::info!("Adding new host {}", fqdn);

        Host::new(fqdn, client_start_time)
    })
}
