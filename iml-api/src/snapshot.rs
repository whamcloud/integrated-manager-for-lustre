// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlApiError;
use futures::{future::try_join, TryFutureExt};
use iml_job_scheduler_rpc::{available_jobs, available_transitions, Job, Transition};
use iml_rabbit::Connection;
use iml_wire_types::{ApiList, AvailableAction, CompositeId};
use std::convert::TryFrom;
use warp::{reply::Json, Filter};

type CompositeIds = Vec<CompositeId>;

fn composite_ids() -> impl Filter<Extract = (CompositeIds,), Error = warp::Rejection> + Clone + Send
{
    warp::query().map(|q: Vec<(String, String)>| {
        q.into_iter()
            .filter(|(x, _)| x == "composite_ids")
            .filter_map(|(_, y)| CompositeId::try_from(y).ok())
            .collect()
    })
}

async fn get_snapshots(
    ids: CompositeIds,
    conn: Connection,
) -> Result<impl warp::Reply, warp::Rejection> {
    drop(conn);

    Ok(warp::reply::json(&()))
}

pub(crate) fn endpoint(
    client_filter: impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone + Send,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path("snapshot")
        .and(warp::get())
        .and(composite_ids())
        .and(client_filter)
        .and_then(get_snapshots)
}
