// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{cache, error::ImlWarpDriveError};
use iml_postgres::PgPool;
use iml_state_machine::{graph::StateGraphExt, run_command, JobStates};
use iml_wire_types::{
    state_machine::{Command, Transition},
    warp_drive::RecordId,
};
use std::sync::Arc;
use warp::Filter;

pub fn route(
    shared_cache: cache::SharedCache,
    job_states: JobStates,
    pg_pool: PgPool,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    let route = warp::path("state_machine");

    let shared_cache_filter = warp::any().map(move || Arc::clone(&shared_cache));

    let get_transitions_route = route
        .clone()
        .and(shared_cache_filter.clone())
        .and(warp::path("get_transitions"))
        .and(warp::path::end())
        .and(warp::post())
        .and(warp::body::json())
        .and_then(
            |shared_cache: cache::SharedCache, record_id: RecordId| async move {
                tracing::debug!("Inside state_machine route");

                let cache = shared_cache.lock().await;

                let g = iml_state_machine::graph::build_graph();

                let x = record_id
                    .to_state(&cache)
                    .and_then(|x| g.get_state_node(x))
                    .map(|x| g.get_available_transitions(x))
                    .unwrap_or_default();

                Ok::<_, warp::Rejection>(warp::reply::json(&x))
            },
        );

    let get_transition_path_route =
        route
            .clone()
            .and(shared_cache_filter)
            .and(warp::path("get_transition_path"))
            .and(warp::path::end())
            .and(warp::post())
            .and(warp::body::json())
            .and_then(
                |shared_cache: cache::SharedCache,
                 (record_id, transition): (RecordId, Transition)| async move {
                    let cache = shared_cache.lock().await;

                    let g = iml_state_machine::graph::build_graph();

                    let xs = record_id
                        .to_state(&cache)
                        .and_then(|x| g.get_transition_path(x, transition))
                        .unwrap_or_default();

                    Ok::<_, warp::Rejection>(warp::reply::json(&xs))
                },
            );

    let run_command_route = route
        .clone()
        .and(warp::path("run_command"))
        .and(warp::path::end())
        .and(warp::post())
        .and(warp::any().map(move || pg_pool.clone()))
        .and(warp::any().map(move || Arc::clone(&job_states)))
        .and(warp::body::json())
        .and_then(
            |pg_pool: PgPool, job_states: JobStates, command: Command| async move {
                let cmd = run_command(&pg_pool, &job_states, command)
                    .await
                    .map_err(ImlWarpDriveError::StateMachineError)
                    .map_err(warp::reject::custom)?;

                Ok::<_, warp::Rejection>(warp::reply::json(&cmd))
            },
        );

    get_transitions_route
        .or(get_transition_path_route)
        .or(run_command_route)
}
