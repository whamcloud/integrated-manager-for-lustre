// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlApiError;
use futures::TryFutureExt;
use iml_orm::{task::ChromaCoreTask, tokio_diesel::AsyncRunQueryDsl as _};
use iml_rabbit::Connection;
use iml_wire_types::{ApiList, CompositeId};
//use std::convert::TryFrom;
use warp::Filter;

async fn create_task(
    client: Connection,
    task: serde_json::Value,
) -> Result<impl warp::Reply, warp::Rejection> {
    let xs: CompositeId = iml_job_scheduler_rpc::call(&client, "create_task", vec![task], None)
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

    Ok(warp::reply::json(&xs))
}

async fn remove_task(
    client: Connection,
    ids: Vec<i32>,
) -> Result<impl warp::Reply, warp::Rejection> {
    let xs: CompositeId = iml_job_scheduler_rpc::call(&client, "remove_task", ids, None)
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;
    Ok(warp::reply::json(&xs))
}

async fn get_tasks() -> Result<impl warp::Reply, warp::Rejection> {
    let pool = iml_orm::pool().map_err(ImlApiError::ImlR2D2Error)?;

    let xs: Vec<ChromaCoreTask> = ChromaCoreTask::all()
        .get_results_async(&pool)
        .map_err(ImlApiError::ImlDieselAsyncError)
        .await?;

    Ok(warp::reply::json(&ApiList::new(xs)))
}

pub(crate) fn endpoint(
    client_filter: impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone + Send,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path("task")
        .and(warp::get().and_then(get_tasks))
        .or(warp::post()
            .and(client_filter.clone())
            .and(warp::body::json())
            .and_then(create_task))
        .or(warp::delete()
            .and(client_filter)
            .and(warp::body::json())
            .and_then(remove_task))
}
