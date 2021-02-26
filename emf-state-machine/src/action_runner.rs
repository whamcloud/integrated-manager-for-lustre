// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use emf_wire_types::{Action, ActionId, ActionName, AgentResult, Fqdn};
use once_cell::sync::Lazy;
use std::{collections::HashMap, sync::Arc};
use tokio::sync::{
    oneshot::{self, Receiver, Sender},
    Mutex,
};
use uuid::Uuid;

pub type OutgoingHostQueues = Arc<Mutex<HashMap<Fqdn, Vec<Action>>>>;

pub static OUTGOING_HOST_QUEUES: Lazy<OutgoingHostQueues> =
    Lazy::new(|| Arc::new(Mutex::new(HashMap::new())));

pub type IncomingHostQueues =
    Arc<Mutex<HashMap<Fqdn, HashMap<ActionId, oneshot::Sender<AgentResult>>>>>;

pub static INCOMING_HOST_QUEUES: Lazy<IncomingHostQueues> =
    Lazy::new(|| Arc::new(Mutex::new(HashMap::new())));

pub async fn invoke_remote(
    fqdn: Fqdn,
    action: ActionName,
    args: serde_json::value::Value,
) -> (Sender<()>, Receiver<AgentResult>) {
    let action_id = ActionId(Uuid::new_v4().to_string());

    let (tx, rx) = oneshot::channel();

    let mut qs = INCOMING_HOST_QUEUES.lock().await;

    let q = qs.entry(fqdn.clone()).or_insert(HashMap::new());
    q.insert(action_id.clone(), tx);

    let mut qs = OUTGOING_HOST_QUEUES.lock().await;

    let q = qs.entry(fqdn.clone()).or_insert(vec![]);

    q.push(Action::ActionStart {
        action,
        id: action_id.clone(),
        args,
    });

    let (tx, rx2) = oneshot::channel();

    let fqdn = fqdn.clone();
    tokio::spawn(async move {
        if rx2.await.is_err() {
            return;
        };

        let mut qs = OUTGOING_HOST_QUEUES.lock().await;

        let q = qs.entry(fqdn.clone()).or_insert(vec![]);
        q.push(Action::ActionCancel { id: action_id });
    });

    (tx, rx)
}
