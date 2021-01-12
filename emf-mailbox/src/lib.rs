// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::Buf;
use emf_postgres::sqlx::{self, PgPool};
use emf_tracing::tracing;
use emf_wire_types::{db::LustreFid, task::Task};
use futures::{stream::BoxStream, Stream, StreamExt, TryFutureExt, TryStreamExt};
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

    emf_fs::read_lines(s)
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

fn convert_lines(lines: Vec<String>) -> Vec<(LustreFid, serde_json::Value)> {
    lines
        .into_iter()
        .filter_map(|x| {
            let incoming = serde_json::from_str(&x);

            let incoming: Incoming = match incoming {
                Ok(x) => x,
                Err(e) => {
                    tracing::info!("Unable to convert line {} Error: {:?}", x, e);

                    return None;
                }
            };

            let data = match incoming.data.into_iter().next() {
                Some((_, v)) => v,
                None => json!({}),
            };

            let fid = LustreFid::from_str(&incoming.fid);

            let fid = match fid {
                Ok(x) => x,
                Err(e) => {
                    tracing::info!("Unable to convert fid {} Error: {:?}", x, e);

                    return None;
                }
            };

            Some((fid, data))
        })
        .collect()
}

async fn insert_lines(
    lines: &[(LustreFid, serde_json::Value)],
    task: &Task,
    pool: &PgPool,
) -> Result<(), MailboxError> {
    let x = lines
        .iter()
        .fold((vec![], vec![], vec![], vec![]), |mut acc, (fid, value)| {
            acc.0.push(fid.seq);
            acc.1.push(fid.oid);
            acc.2.push(fid.ver);
            acc.3.push(value.clone());

            acc
        });

    sqlx::query!(
        r#"
            INSERT INTO chroma_core_fidtaskqueue (fid, data, task_id)
            SELECT row(seq, oid, ver)::lustre_fid, data, $5
            FROM UNNEST($1::bigint[], $2::int[], $3::int[], $4::jsonb[])
            AS t(seq, oid, ver, data)"#,
        &x.0,
        &x.1,
        &x.2,
        &x.3,
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

    let lines = convert_lines(lines);

    let count = lines.len();

    insert_lines(&lines, &task, &pool)
        .inspect_err(|e| {
            tracing::info!("Unable to process lines {:?}: Error: {:?}", lines, e);
        })
        .await?;

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
