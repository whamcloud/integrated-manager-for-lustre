// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![type_length_limit = "2097152"]

use futures::{sync::oneshot, Future as _};
use iml_agent_comms::messaging::consume_agent_tx_queue;
use iml_services::services::action_runner::{
    data::{
        has_action_in_flight, remove_action_in_flight, ActionInFlight, SessionToRpcs, Sessions,
        Shared,
    },
    sender::sender,
};
use iml_wire_types::{Action, ActionId, ActionName, Fqdn, Id};
use lapin_futures::client::ConnectionOptions;
use parking_lot::Mutex;
use rand::distributions::Alphanumeric;
use rand::{thread_rng, Rng};
use std::{collections::HashMap, sync::Arc};
use tokio::runtime::Runtime;
use warp::{self, Filter};

fn create_random_string() -> String {
    thread_rng().sample_iter(&Alphanumeric).take(5).collect()
}

fn create_test_connection() -> impl iml_rabbit::TcpClientFuture {
    let addr = "127.0.0.1:5672".to_string().parse().unwrap();

    iml_rabbit::connect(&addr, ConnectionOptions::default()).map(|(client, mut heartbeat)| {
        let handle = heartbeat.handle().unwrap();

        handle.stop();

        client
    })
}

fn create_shared_state() -> (Shared<Sessions>, Shared<SessionToRpcs>) {
    let sessions: Shared<Sessions> = Arc::new(Mutex::new(HashMap::new()));
    let session_to_rpcs: Shared<SessionToRpcs> = Arc::new(Mutex::new(HashMap::new()));

    (sessions, session_to_rpcs)
}

fn create_client_filter(
) -> impl Filter<Extract = (iml_rabbit::TcpClient,), Error = warp::Rejection> + Clone {
    warp::any().and_then(|| create_test_connection().map_err(warp::reject::custom))
}

#[test]
fn test_sender_only_accepts_post() {
    let (sessions, session_to_rpcs) = create_shared_state();
    let client_filter = create_client_filter();

    let filter = sender(
        "foo",
        Arc::clone(&sessions),
        Arc::clone(&session_to_rpcs),
        client_filter,
    )
    .map(|x| warp::reply::json(&x));

    let res = warp::test::request().path("/").reply(&filter);
    assert_eq!(res.status(), 405, "GET is not allowed");
}

#[test]
fn test_data_sent_to_active_session() -> Result<(), failure::Error> {
    let queue_name = create_random_string();
    let queue_name2 = queue_name.clone();

    let (sessions, session_to_rpcs) = create_shared_state();
    let client_filter = create_client_filter();

    let filter = sender(
        queue_name,
        Arc::clone(&sessions),
        Arc::clone(&session_to_rpcs),
        client_filter,
    )
    .map(|x| warp::reply::json(&x));

    let fqdn = Fqdn("host1".to_string());
    let id = Id("foo".to_string());
    let action_id = ActionId("1234".to_string());

    sessions.lock().insert(fqdn.clone(), id.clone());

    let action = Action::ActionStart {
        action: ActionName("erase".to_string()),
        args: serde_json::Value::Array(vec![]),
        id: action_id.clone(),
    };

    let mut rt = Runtime::new()?;

    rt.spawn(
        create_test_connection()
            .and_then(iml_rabbit::create_channel)
            .and_then(|ch| consume_agent_tx_queue(ch, queue_name2))
            .map(move |_| {
                while let Some(af) =
                    remove_action_in_flight(&id, &action_id, &mut session_to_rpcs.lock())
                {
                    af.complete(Ok(serde_json::Value::String("ALL DONE!!!1!".to_string())))
                        .unwrap();
                }
            })
            .map_err(|e| panic!("Got an error {:?}", e)),
    );

    let res = warp::test::request()
        .path("/")
        .method("POST")
        .json(&(fqdn, action))
        .reply(&filter);

    assert_eq!(res.status(), 200);

    let body: Result<serde_json::Value, String> = serde_json::from_slice(res.body())?;

    assert_eq!(
        body.unwrap(),
        serde_json::Value::String("ALL DONE!!!1!".to_string())
    );

    Ok(())
}

#[test]
fn test_cancel_sent_to_active_session() -> Result<(), failure::Error> {
    let queue_name = create_random_string();
    let queue_name2 = queue_name.clone();

    let (sessions, session_to_rpcs) = create_shared_state();
    let client_filter = create_client_filter();

    let filter = sender(
        queue_name,
        Arc::clone(&sessions),
        Arc::clone(&session_to_rpcs),
        client_filter,
    )
    .map(|x| warp::reply::json(&x));

    let fqdn = Fqdn("host1".into());
    let id = Id("foo".into());
    let action_id = ActionId("3456".into());

    sessions.lock().insert(fqdn.clone(), id.clone());

    let start_action = Action::ActionStart {
        action: ActionName("erase".to_string()),
        args: serde_json::Value::Array(vec![]),
        id: action_id.clone(),
    };

    let (tx, rx) = oneshot::channel();

    let action_in_flight = ActionInFlight::new(start_action, tx);

    let mut rpcs = HashMap::new();
    rpcs.insert(action_id.clone(), action_in_flight);
    session_to_rpcs.lock().insert(id.clone(), rpcs);

    let cancel_action = Action::ActionCancel {
        id: action_id.clone(),
    };

    let mut rt = Runtime::new()?;

    rt.spawn(
        create_test_connection()
            .and_then(iml_rabbit::create_channel)
            .and_then(|ch| consume_agent_tx_queue(ch, queue_name2))
            .map(move |_| ())
            .map_err(|e| panic!("Got an error {:?}", e)),
    );

    let res = warp::test::request()
        .path("/")
        .method("POST")
        .json(&(fqdn, cancel_action))
        .reply(&filter);

    assert_eq!(res.status(), 200);

    let body: Result<serde_json::Value, String> = serde_json::from_slice(res.body())?;

    assert_eq!(body.unwrap(), serde_json::Value::Null);

    let actual = rt.block_on(rx).unwrap();

    assert_eq!(actual, Ok(serde_json::Value::Null));

    assert_eq!(
        has_action_in_flight(&id, &action_id, &session_to_rpcs.lock()),
        false
    );

    Ok(())
}
