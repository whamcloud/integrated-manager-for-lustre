// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::Buf;
use futures::{future::join_all, stream::BoxStream, Stream, StreamExt, TryFutureExt, TryStreamExt};
use iml_postgres::sqlx::{self, PgPool};
use iml_tracing::tracing;
use iml_wire_types::{db::LustreFid, Task};
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
    SqlxError(#[from] sqlx::Error),
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

async fn get_task_by_name(x: impl ToString, pool: &PgPool) -> Result<Option<Task>, MailboxError> {
    let x = sqlx::query_as!(
        Task,
        "SELECT * FROM chroma_core_task WHERE name = $1",
        &x.to_string()
    )
    .fetch_optional(pool)
    .await?;

    Ok(x)
}

#[derive(serde::Serialize, serde::Deserialize)]
struct Incoming {
    fid: String,
    #[serde(flatten)]
    data: HashMap<String, serde_json::Value>,
}

async fn insert_line(line: &str, task: &Task, pool: &PgPool) -> Result<(), MailboxError> {
    let incoming: Incoming = serde_json::from_str(&line)?;

    let data = match incoming.data.into_iter().next() {
        Some((_, v)) => v,
        None => json!({}),
    };

    let fid = LustreFid::from_str(&incoming.fid)?;

    tracing::trace!("Inserting fid:{:?} data:{:?} task:{:?}", fid, data, task);

    sqlx::query!(
        r#"
            INSERT INTO chroma_core_fidtaskqueue (fid, data, task_id)
            VALUES ($1, $2, $3)"#,
        fid as LustreFid,
        data,
        task.id
    )
    .execute(pool)
    .await?;

    Ok(())
}

/// Given an task name and `mpsc::UnboundedReceiver` handle, this fn
/// will process incoming lines and write them into FidTaskQueue
/// associating the new item with the existing named task.
pub async fn ingest_data(
    pool: PgPool,
    task: String,
    lines: Vec<String>,
) -> Result<(), MailboxError> {
    tracing::debug!("Starting ingest for {} ({} lines)", &task, lines.len());

    let task = match get_task_by_name(&task, &pool).await? {
        Some(t) => t,
        None => {
            tracing::error!("Task {} not found", &task);

            return Err(MailboxError::NotFound(format!("Failed to find {}", &task)));
        }
    };

    let xs = lines.iter().map(|line| {
        tracing::trace!("handling line {:?}", line);

        insert_line(line, &task, &pool).inspect_err(move |e| {
            tracing::info!("Unable to process line {}: Error: {:?}", line, e);
        })
    });

    let count = join_all(xs).await.into_iter().filter(|x| x.is_ok()).count();

    tracing::debug!("Increasing task {} ({}) by {}", task.name, task.id, count);

    sqlx::query!(
        r#"
        UPDATE chroma_core_task
        SET fids_total = fids_total + $1
        WHERE id = $2
    "#,
        count as i64,
        task.id
    )
    .execute(&pool)
    .await?;

    Ok(())
}
