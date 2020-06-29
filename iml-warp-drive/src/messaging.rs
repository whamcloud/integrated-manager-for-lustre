// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{cache, error, locks::SharedLocks, users};
use futures::TryFutureExt;
use std::sync::Arc;
use warp::Filter;

pub fn route(
    user_state: users::SharedUsers,
    api_cache_state: cache::SharedCache,
    lock_state: SharedLocks,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path("messaging")
        .and(warp::get())
        .and(warp::any().map(move || Arc::clone(&user_state)))
        .and(warp::any().map(move || Arc::clone(&lock_state)))
        .and(warp::any().map(move || Arc::clone(&api_cache_state)))
        .and_then(
            |users: users::SharedUsers, locks: SharedLocks, api_cache: cache::SharedCache| {
                tracing::debug!("Inside messaging route");

                async move {
                    // reply using server-sent events
                    let stream = users::user_connected(
                        users,
                        locks.lock().await.clone(),
                        api_cache.lock().await.clone(),
                    )
                    .await;

                    Ok::<_, error::ImlWarpDriveError>(warp::sse::reply(
                        warp::sse::keep_alive().stream(stream),
                    ))
                }
                .map_err(warp::reject::custom)
            },
        )
        .with(warp::log("iml-warp-drive::messaging"))
}
