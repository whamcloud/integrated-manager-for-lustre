// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use dotenv::dotenv;
use emf_action_runner::{
    data::{has_action_in_flight, remove_action_in_flight, ActionInFlight, SessionToRpcs},
    error::ActionRunnerError,
    local_actions::SharedLocalActionsInFlight,
    sender::sender,
    Sessions, Shared,
};
use emf_agent_comms::messaging::consume_agent_tx_queue;
use emf_postgres::get_db_pool;
use emf_rabbit::ConnectionProperties;
use emf_wire_types::{Action, ActionId, ActionName, ActionType, Fqdn, Id};
use futures::{channel::oneshot, lock::Mutex, StreamExt, TryFutureExt, TryStreamExt};
use rand::{distributions::Alphanumeric, thread_rng, Rng};
use std::{collections::HashMap, sync::Arc, time::Duration};
use tokio::time::delay_for;
use warp::{self, Filter};

fn create_random_string() -> String {
    thread_rng().sample_iter(&Alphanumeric).take(5).collect()
}

async fn create_test_connection() -> Result<emf_rabbit::Connection, emf_rabbit::EmfRabbitError> {
    let pool = emf_rabbit::create_pool(
        "amqp://127.0.0.1:5672//".to_string(),
        1,
        ConnectionProperties::default(),
    );

    emf_rabbit::get_conn(pool).await
}

fn create_shared_state() -> (
    Shared<Sessions>,
    Shared<SessionToRpcs>,
    SharedLocalActionsInFlight,
) {
    let sessions: Shared<Sessions> = Arc::new(Mutex::new(HashMap::new()));
    let session_to_rpcs: Shared<SessionToRpcs> = Arc::new(Mutex::new(HashMap::new()));
    let local_actions: SharedLocalActionsInFlight = Arc::new(Mutex::new(HashMap::new()));

    (sessions, session_to_rpcs, local_actions)
}

fn create_client_filter(
) -> impl Filter<Extract = (emf_rabbit::Connection,), Error = warp::Rejection> + Clone {
    warp::any().and_then(|| create_test_connection().map_err(|_| warp::reject::not_found()))
}

#[tokio::test]
#[ignore = "Requires an active DB"]
async fn test_sender_only_accepts_post() -> Result<(), Box<dyn std::error::Error>> {
    dotenv().ok();

    let (sessions, session_to_rpcs, local_actions) = create_shared_state();
    let client_filter = create_client_filter();

    let pool = get_db_pool(5).await?;

    let filter = sender(
        "foo",
        Arc::clone(&sessions),
        Arc::clone(&session_to_rpcs),
        Arc::clone(&local_actions),
        client_filter,
        pool,
    )
    .map(|x| warp::reply::json(&x));

    let res = warp::test::request().path("/").reply(&filter).await;
    assert_eq!(res.status(), 405, "GET is not allowed");

    Ok(())
}

#[tokio::test]
#[ignore = "Requires an active DB"]
async fn test_data_sent_to_active_session() -> Result<(), Box<dyn std::error::Error>> {
    dotenv().ok();

    let queue_name = create_random_string();
    let queue_name2 = queue_name.clone();

    let (sessions, session_to_rpcs, local_actions) = create_shared_state();
    let client_filter = create_client_filter();

    let pool = get_db_pool(5).await?;

    let filter = sender(
        queue_name,
        Arc::clone(&sessions),
        Arc::clone(&session_to_rpcs),
        Arc::clone(&local_actions),
        client_filter,
        pool,
    )
    .map(|x| warp::reply::json(&x));

    let fqdn = Fqdn("host1".into());
    let id = Id("foo".into());
    let action_id = ActionId("1234".into());

    sessions.lock().await.insert(fqdn.clone(), id.clone());

    let action = ActionType::Remote((
        fqdn,
        Action::ActionStart {
            action: ActionName("erase".to_string()),
            args: serde_json::Value::Array(vec![]),
            id: action_id.clone(),
        },
    ));

    tokio::spawn(
        async move {
            let conn = create_test_connection().await?;

            let ch = emf_rabbit::create_channel(&conn).await?;

            let _ = consume_agent_tx_queue(&ch, queue_name2)
                .await?
                .into_future()
                .await;

            let af = loop {
                let x = session_to_rpcs
                    .try_lock()
                    .and_then(|mut lock| remove_action_in_flight(&id, &action_id, &mut lock));

                if let Some(x) = x {
                    break x;
                }

                delay_for(Duration::from_millis(10)).await;
            };

            af.complete(Ok(serde_json::Value::String("ALL DONE!!!1!".to_string())))
                .unwrap();

            Ok(())
        }
        .unwrap_or_else(|e: ActionRunnerError| panic!("{}", e)),
    );

    let res = warp::test::request()
        .method("POST")
        .json(&action)
        .reply(&filter)
        .await;

    assert_eq!(res.status(), 200, "{:?}", res.body());

    let body: Result<serde_json::Value, String> = serde_json::from_slice(res.body())?;

    assert_eq!(
        body.unwrap(),
        serde_json::Value::String("ALL DONE!!!1!".to_string())
    );

    Ok(())
}

#[tokio::test]
#[ignore = "Requires an active DB"]
async fn test_cancel_sent_to_active_session() -> Result<(), Box<dyn std::error::Error>> {
    dotenv().ok();

    let queue_name = create_random_string();
    let queue_name2 = queue_name.clone();

    let (sessions, session_to_rpcs, local_actions) = create_shared_state();
    let client_filter = create_client_filter();

    let pool = get_db_pool(5).await?;

    let filter = sender(
        queue_name,
        Arc::clone(&sessions),
        Arc::clone(&session_to_rpcs),
        Arc::clone(&local_actions),
        client_filter,
        pool,
    )
    .map(|x| warp::reply::json(&x));

    let fqdn = Fqdn("host1".into());
    let id = Id("foo".into());
    let action_id = ActionId("3456".into());

    sessions.lock().await.insert(fqdn.clone(), id.clone());

    let start_action = Action::ActionStart {
        action: ActionName("erase".to_string()),
        args: serde_json::Value::Array(vec![]),
        id: action_id.clone(),
    };

    let (tx, rx) = oneshot::channel();

    let action_in_flight = ActionInFlight::new(start_action, tx);

    let mut rpcs = HashMap::new();
    rpcs.insert(action_id.clone(), action_in_flight);
    session_to_rpcs.lock().await.insert(id.clone(), rpcs);

    let cancel_action = ActionType::Remote((
        fqdn,
        Action::ActionCancel {
            id: action_id.clone(),
        },
    ));

    tokio::spawn(
        async move {
            let conn = create_test_connection().await?;

            let ch = emf_rabbit::create_channel(&conn).await?;

            consume_agent_tx_queue(&ch, queue_name2)
                .await?
                .try_collect::<Vec<_>>()
                .await?;

            Ok(())
        }
        .unwrap_or_else(|e: ActionRunnerError| panic!("{}", e)),
    );

    let res = warp::test::request()
        .method("POST")
        .json(&cancel_action)
        .reply(&filter)
        .await;

    assert_eq!(res.status(), 200, "{:?}", res.body());

    let body: Result<serde_json::Value, String> = serde_json::from_slice(res.body())?;

    assert_eq!(body.unwrap(), serde_json::Value::Null);

    let actual = rx.await?;

    assert_eq!(actual, Ok(serde_json::Value::Null));

    let lock = session_to_rpcs.lock().await;

    assert_eq!(has_action_in_flight(&id, &action_id, &lock), false);

    Ok(())
}
