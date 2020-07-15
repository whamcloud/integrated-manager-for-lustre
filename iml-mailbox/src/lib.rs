// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::Buf;
use futures::{future::join_all, stream::BoxStream, Stream, StreamExt, TryStreamExt};
use iml_orm::{
    fidtaskqueue::insert_fidtask,
    lustrefid::LustreFid,
    task::{self, ChromaCoreTask as Task},
    tokio_diesel::{AsyncRunQueryDsl as _, OptionalExtension as _},
};
use iml_tracing::tracing;
use serde_json::json;
use std::{collections::HashMap, str::FromStr};
use thiserror::Error;
use warp::{filters::BoxedFilter, reject, Filter};

#[derive(Error, Debug)]
pub enum MailboxError {
    #[error(transparent)]
    IoError(#[from] std::io::Error),
    #[error(transparent)]
    JsonError(#[from] serde_json::error::Error),
    #[error("Not found: {0}")]
    NotFound(String),
    #[error(transparent)]
    ParseIntError(#[from] std::num::ParseIntError),
    #[error(transparent)]
    ImlOrmError(#[from] iml_orm::ImlOrmError),
    #[error(transparent)]
    TokioAsyncError(#[from] iml_orm::tokio_diesel::AsyncError),
}

impl reject::Reject for MailboxError {}

pub trait LineStream: Stream<Item = Result<String, warp::Rejection>> {}
impl<T: Stream<Item = Result<String, warp::Rejection>>> LineStream for T {}

fn streamer<'a>(
    s: impl Stream<Item = Result<impl Buf, warp::Error>> + Send + 'a,
) -> BoxStream<'a, Result<String, warp::Rejection>> {
    let s = s.map_ok(|mut x| x.to_bytes());

    iml_fs::read_lines(s)
        .map_err(MailboxError::IoError)
        .map_err(reject::custom)
        .boxed()
}

/// Warp Filter that streams a newline delimited body
pub fn line_stream<'a>() -> BoxedFilter<(BoxStream<'a, Result<String, warp::Rejection>>,)> {
    warp::body::stream().map(streamer).boxed()
}

async fn get_task_by_name(
    x: impl ToString,
    pool: &iml_orm::DbPool,
) -> Result<Option<Task>, iml_orm::tokio_diesel::AsyncError> {
    Task::by_name(x).first_async(pool).await.optional()
}

/// Given an task name and `mpsc::UnboundedReceiver` handle, this fn
/// will process incoming lines and write them into FidTaskQueue
/// associating the new item with the existing named task.
pub async fn ingest_data(task: String, lines: Vec<String>) -> Result<(), MailboxError> {
    tracing::debug!("Starting ingest for {}", &task);

    let pool = iml_orm::pool()?;

    let task = match get_task_by_name(&task, &pool).await? {
        Some(t) => t,
        None => {
            tracing::error!("Task {} not found", &task);

            return Err(MailboxError::NotFound(format!("Failed to find {}", &task)));
        }
    };

    let xs = lines.iter().filter_map(|line| {
        tracing::trace!("handling line {:?}", &line);

        let mut map: HashMap<String, serde_json::Value> = serde_json::from_str(&line).ok()?;

        if let Some(fid) = map.remove("fid".into()) {
            let fid = LustreFid::from_str(
                fid.as_str()
                    .ok_or_else(|| {
                        MailboxError::NotFound(format!("Failed to find fid in {}", line))
                    })
                    .ok()?,
            )
            .ok()?;

            // Get "other" data if it exists
            let data = match map.iter().next() {
                Some((_, v)) => v.clone(),
                None => json!({}),
            };

            tracing::trace!("Inserting fid:{:?} data:{:?} task:{:?}", fid, data, task);

            Some(insert_fidtask(fid, data, &task).execute_async(&pool))
        } else {
            tracing::error!("Failed to process {:?}", &line);
            None
        }
    });

    let count = join_all(xs).await.into_iter().filter(|x| x.is_ok()).count();

    tracing::debug!("Increasing task {} ({}) by {}", task.name, task.id, count);

    task::increase_total(task.id, count as i64)
        .execute_async(&pool)
        .await?;

    Ok(())
}
