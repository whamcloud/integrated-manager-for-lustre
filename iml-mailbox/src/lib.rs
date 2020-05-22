// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::Buf;
use futures::{
    channel::{mpsc, oneshot},
    stream::BoxStream,
    Future, Stream, StreamExt, TryStreamExt,
};
use iml_orm::{
    fidtaskqueue::insert_fidtask,
    lustrefid::LustreFid,
    task::ChromaCoreTask as Task,
    tokio_diesel::{AsyncRunQueryDsl as _, OptionalExtension as _},
};
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
    #[error(transparent)]
    TrySendError(#[from] futures::channel::mpsc::TrySendError<Incoming>),
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

pub enum Incoming {
    Line(String),
    EOF(oneshot::Sender<()>),
}

impl Incoming {
    pub fn create_eof() -> (Self, oneshot::Receiver<()>) {
        let (tx, rx) = oneshot::channel();

        (Incoming::EOF(tx), rx)
    }
}

/// Warp Filter that streams a newline delimited body
pub fn line_stream<'a>() -> BoxedFilter<(BoxStream<'a, Result<String, warp::Rejection>>,)> {
    warp::body::stream().map(streamer).boxed()
}

/// Holds all active streams that are currently writing to a task.
pub struct MailboxSenders(HashMap<String, mpsc::UnboundedSender<Incoming>>);

impl Default for MailboxSenders {
    fn default() -> Self {
        MailboxSenders(HashMap::new())
    }
}

impl MailboxSenders {
    /// Adds a new task and tx handle to write lines with
    pub fn insert(&mut self, task: String, tx: mpsc::UnboundedSender<Incoming>) {
        self.0.insert(task, tx);
    }
    /// Removes an task.
    ///
    /// Usually called when the associated rx stream has finished.
    pub fn remove(&mut self, task: &String) {
        self.0.remove(task);
    }
    /// Returns a cloned reference to a tx handle matching the provided task, if one exists.
    pub fn get(&mut self, task: &String) -> Option<mpsc::UnboundedSender<Incoming>> {
        self.0.get(task).cloned()
    }
    /// Creates a new sender entry.
    ///
    /// Returns a pair of tx handle and a future that will write to a file.
    /// The returned future must be used, and should be spawned as a new task
    /// so it won't block the current task.
    pub fn create(
        &mut self,
        task: String,
    ) -> (
        mpsc::UnboundedSender<Incoming>,
        impl Future<Output = Result<(), MailboxError>>,
    ) {
        let (tx, rx) = mpsc::unbounded();

        self.insert(task.clone(), tx.clone());

        (tx, ingest_data(task, rx))
    }
}

async fn get_task_by_name(
    x: impl ToString,
    pool: &iml_orm::DbPool,
) -> Result<Option<Task>, iml_orm::tokio_diesel::AsyncError> {
    Task::by_name(x).first_async(pool).await.optional()
}

/// Given an task name and `mpsc::UnboundedReceiver` handle,
/// this fn will create or open an existing file in append mode.
///
/// It will then write any incoming lines from the passed `mpsc::UnboundedReceiver`
/// to that file.
pub async fn ingest_data(
    task: String,
    mut rx: mpsc::UnboundedReceiver<Incoming>,
) -> Result<(), MailboxError> {
    tracing::info!("Starting ingest for {:?}", task);

    let pool = iml_orm::pool()?;

    let task = match get_task_by_name(&task, &pool).await? {
        Some(t) => t,
        None => {
            tracing::info!("Task {} not found.  Creating.", task);

            return Err(MailboxError::NotFound(format!("Failed to find {}", task)));
        }
    };

    while let Some(incoming) = rx.next().await {
        match incoming {
            Incoming::Line(line) => {
                tracing::trace!("handling line {:?}", &line);

                let mut map: HashMap<String, serde_json::Value> = serde_json::from_str(&line)?;

                if let Some(fid) = map.remove("fid".into()) {
                    let fid = LustreFid::from_str(fid.as_str().ok_or(MailboxError::NotFound(
                        format!("Failed to find fid in {}", line),
                    ))?)?;

                    // Get "other" data if it exists
                    let data = match map.iter().next() {
                        Some((_, v)) => v.clone(),
                        None => json!({}),
                    };

                    tracing::trace!("Inserting fid:{:?} data:{:?} task:{:?}", fid, data, task);
                    insert_fidtask(fid, data, &task)
                        .execute_async(&pool)
                        .await?;
                } else {
                    tracing::error!("No FID for task {} in line {:?}", &task.name, &line);
                }
            }
            Incoming::EOF(tx) => {
                let _ = tx.send(());
            }
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempdir::TempDir;

    #[tokio::test]
    async fn test_mailbox_senders() -> Result<(), Box<dyn std::error::Error>> {
        let tmp_dir = TempDir::new("test_mailbox")?;
        let address = tmp_dir.path().join("test_message_1");

        let mut mailbox_sender = MailboxSenders::default();

        let (tx, fut) = mailbox_sender.create(address.clone());

        tx.unbounded_send(Incoming::Line("foo\n".into()))?;

        mailbox_sender
            .get(&address)
            .unwrap()
            .unbounded_send(Incoming::Line("bar".into()))?;

        tx.unbounded_send(Incoming::Line("baz\n".into()))?;

        mailbox_sender.remove(&address);

        drop(tx);

        fut.await?;

        let contents = fs::read_to_string(&address).unwrap();

        assert_eq!(contents, "foo\nbar\nbaz\n");

        Ok(())
    }
}
