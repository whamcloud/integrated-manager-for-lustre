// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use emf_lib_state_machine::input_document::deserialize_input_document;
use emf_manager_env::get_pool_limit;
use emf_postgres::get_db_pool;
use emf_state_machine::{
    action_runner::{
        IncomingHostQueues, OutgoingHostQueues, INCOMING_HOST_QUEUES, OUTGOING_HOST_QUEUES,
    },
    command_plan::{build_command, build_job_graphs, JobGraphs},
    executor::get_executor,
    Error,
};
use emf_tracing::tracing;
use emf_wire_types::{ActionResult, Fqdn};
use futures::TryFutureExt;
use petgraph::graph::NodeIndex;
use std::{convert::Infallible, sync::Arc};
use tokio::sync::mpsc::UnboundedSender;
use warp::{http, hyper::body::Bytes, Filter as _, Reply as _};

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

#[tokio::main]
async fn main() -> Result<(), Error> {
    emf_tracing::init();

    let pool = get_db_pool(
        get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT),
        emf_manager_env::get_port("STATE_MACHINE_SERVICE_PG_PORT"),
    )
    .await?;

    sqlx::migrate!("../migrations").run(&pool).await?;

    let tx = get_executor(&pool);

    let get_actions = warp::get()
        .and(warp::header("x-client-fqdn"))
        .and(warp::header("x-instance-id"))
        .and(warp::any().map(move || Arc::clone(&OUTGOING_HOST_QUEUES)))
        .and_then(
            |fqdn: Fqdn, instance_id: String, outgoing_queues: OutgoingHostQueues| async move {
                let mut outgoing_queues = outgoing_queues.lock().await;

                let queue = outgoing_queues.entry(fqdn).or_insert(vec![]);

                let xs: Vec<_> = queue.drain(..).collect();

                Ok::<_, Infallible>(warp::reply::json(&xs))
            },
        );

    let submit_document = warp::post()
        .and(warp::path("submit"))
        .and(warp::body::bytes())
        .and(warp::any().map(move || pool.clone()))
        .and(warp::any().map(move || tx.clone()))
        .and_then(
            |x: Bytes, pg_pool, tx: UnboundedSender<(i32, JobGraphs, Vec<NodeIndex>)>| {
                async move {
                    let x = match deserialize_input_document(x) {
                        Ok(x) => x,
                        Err(e) => {
                            return Ok(warp::reply::with_status(
                                e.to_string(),
                                http::StatusCode::BAD_REQUEST,
                            )
                            .into_response())
                        }
                    };

                    let input_doc_json: serde_json::Value = serde_json::to_value(&x)?;

                    let graphs = build_job_graphs(x);

                    let sorted_jobs = match petgraph::algo::toposort(&graphs, None) {
                        Ok(x) => x,
                        Err(e) => {
                            let msg = format!(
                                "This graph has a cycle at job {:?}. It will not be processed",
                                &(graphs[e.node_id()]).0
                            );

                            tracing::error!("{}", &msg);

                            return Ok(warp::reply::with_status(
                                msg,
                                http::StatusCode::BAD_REQUEST,
                            )
                            .into_response());
                        }
                    };

                    let cmd = build_command(&pg_pool, &graphs).await?;

                    sqlx::query!(
                        r#"
                    INSERT INTO input_document (document)
                    VALUES ($1)
                    "#,
                        input_doc_json
                    )
                    .execute(&pg_pool)
                    .await?;

                    let _ = tx.send((cmd.id, graphs, sorted_jobs));

                    Ok::<_, Error>(warp::reply::json(&cmd).into_response())
                }
                .map_err(warp::reject::custom)
            },
        );

    let ingest_responses = warp::post()
        .and(warp::header("x-client-fqdn"))
        .and(warp::header("x-instance-id"))
        .and(warp::body::json())
        .and(warp::any().map(move || Arc::clone(&INCOMING_HOST_QUEUES)))
        .and_then(
            |fqdn: Fqdn,
             instance_id: String,
             ActionResult { id, result },
             incoming_queues: IncomingHostQueues| async move {
                let mut incoming_queues = incoming_queues.lock().await;

                let queue = match incoming_queues.get_mut(&fqdn) {
                    Some(x) => x,
                    None => {
                        return Ok(warp::reply::with_status(
                            "FQDN not found",
                            http::StatusCode::BAD_REQUEST,
                        )
                        .into_response())
                    }
                };

                let tx = match queue.remove(&id) {
                    Some(x) => x,
                    None => {
                        return Ok(warp::reply::with_status(
                            "Action Id not found",
                            http::StatusCode::BAD_REQUEST,
                        )
                        .into_response())
                    }
                };

                let _ = tx.send(result);

                Ok::<_, Infallible>(http::StatusCode::ACCEPTED.into_response())
            },
        );

    let port = emf_manager_env::get_port("STATE_MACHINE_SERVICE_PORT");

    warp::serve(get_actions.or(submit_document).or(ingest_responses))
        .run(([127, 0, 0, 1], port))
        .await;

    Ok(())
}
