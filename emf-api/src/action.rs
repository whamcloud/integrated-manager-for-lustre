// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::EmfApiError;
use emf_job_scheduler_rpc::{available_jobs, available_transitions, Job, Transition};
use emf_rabbit::Connection;
use emf_wire_types::{ApiList, AvailableAction, CompositeId};
use futures::{future::try_join, TryFutureExt};
use std::convert::TryFrom;
use warp::Filter;

fn composite_ids() -> impl Filter<Extract = (CompositeIds,), Error = warp::Rejection> + Clone + Send
{
    warp::query().map(|q: Vec<(String, String)>| {
        q.into_iter()
            .filter(|(x, _)| x == "composite_ids")
            .filter_map(|(_, y)| CompositeId::try_from(y).ok())
            .collect()
    })
}

async fn get_actions(
    ids: CompositeIds,
    conn: Connection,
) -> Result<impl warp::Reply, warp::Rejection> {
    let fut1 = available_transitions(&conn, &ids).map_err(EmfApiError::EmfJobSchedulerRpcError);

    let fut2 = available_jobs(&conn, &ids).map_err(EmfApiError::EmfJobSchedulerRpcError);

    let (computed_transitions, computed_jobs) = try_join(fut1, fut2).await?;

    drop(conn);

    let computed_transitions = computed_transitions.into_iter().flat_map(|(x, xs)| {
        xs.into_iter()
            .map(|y| ApiTransition(x.clone(), y))
            .map(|x| x.into())
            .collect::<Vec<AvailableAction>>()
    });

    let computed_jobs = computed_jobs.into_iter().flat_map(|(x, xs)| {
        xs.into_iter()
            .map(|y| ApiJob(x.clone(), y))
            .map(|x| x.into())
            .collect::<Vec<AvailableAction>>()
    });

    let mut xs: Vec<_> = computed_transitions.chain(computed_jobs).collect();

    xs.sort_by(|a, b| a.display_order.cmp(&b.display_order));

    Ok(warp::reply::json(&ApiList::new(xs)))
}

pub(crate) fn endpoint(
    client_filter: impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone + Send,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path("action")
        .and(warp::get())
        .and(composite_ids())
        .and(client_filter)
        .and_then(get_actions)
}

struct ApiTransition(CompositeId, Transition);

impl From<ApiTransition> for AvailableAction {
    fn from(x: ApiTransition) -> Self {
        AvailableAction {
            args: None,
            composite_id: x.0,
            class_name: None,
            confirmation: None,
            display_group: x.1.display_group,
            display_order: x.1.display_order,
            long_description: x.1.long_description,
            state: Some(x.1.state),
            verb: x.1.verb,
        }
    }
}

struct ApiJob(CompositeId, Job);

impl From<ApiJob> for AvailableAction {
    fn from(ApiJob(composite_id, job): ApiJob) -> Self {
        AvailableAction {
            args: job.args,
            composite_id,
            class_name: job.class_name,
            confirmation: job.confirmation,
            display_group: job.display_group,
            display_order: job.display_order,
            long_description: job.long_description,
            state: None,
            verb: job.verb,
        }
    }
}

type CompositeIds = Vec<CompositeId>;

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_composite_ids_to_query_string() {
        let v: Vec<_> = warp::test::request()
            .path("/?composite_ids=1:2&composite_ids=3:4")
            .filter(&composite_ids())
            .await
            .unwrap();

        assert_eq!(v, vec![CompositeId(1, 2), CompositeId(3, 4)]);
    }

    #[tokio::test]
    async fn test_no_composite_ids() {
        let v: Vec<_> = warp::test::request()
            .path("/")
            .filter(&composite_ids())
            .await
            .unwrap();

        assert_eq!(v, vec![]);
    }
}
