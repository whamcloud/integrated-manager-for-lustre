// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::Buf;
use futures::{
    channel::{mpsc, oneshot},
    stream::BoxStream,
    Future, Stream, StreamExt, TryStreamExt,
};
use std::{collections::HashMap, path::PathBuf};
use tokio::{fs::OpenOptions, io::AsyncWriteExt};
use warp::{filters::BoxedFilter, reject, Filter};

#[derive(Debug)]
pub enum Errors {
    IoError(std::io::Error),
    TrySendError(mpsc::TrySendError<Incoming>),
}

impl reject::Reject for Errors {}

pub trait LineStream: Stream<Item = Result<String, warp::Rejection>> {}
impl<T: Stream<Item = Result<String, warp::Rejection>>> LineStream for T {}

fn streamer<'a>(
    s: impl Stream<Item = Result<impl Buf, warp::Error>> + Send + 'a,
) -> BoxStream<'a, Result<String, warp::Rejection>> {
    let s = s.map_ok(|mut x| x.copy_to_bytes(x.remaining()));

    emf_fs::read_lines(s)
        .map_err(Errors::IoError)
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

/// Holds all active streams that are currently writing to an address.
pub struct ReportSenders(HashMap<PathBuf, mpsc::UnboundedSender<Incoming>>);

impl Default for ReportSenders {
    fn default() -> Self {
        ReportSenders(HashMap::new())
    }
}

impl ReportSenders {
    /// Adds a new address and tx handle to write lines with
    pub fn insert(&mut self, address: PathBuf, tx: mpsc::UnboundedSender<Incoming>) {
        self.0.insert(address, tx);
    }
    /// Removes an address.
    ///
    /// Usually called when the associated rx stream has finished.
    pub fn remove(&mut self, address: &PathBuf) {
        self.0.remove(address);
    }
    /// Returns a cloned reference to a tx handle matching the provided address, if one exists.
    pub fn get(&mut self, address: &PathBuf) -> Option<mpsc::UnboundedSender<Incoming>> {
        self.0.get(address).cloned()
    }
    /// Creates a new sender entry.
    ///
    /// Returns a pair of tx handle and a future that will write to a file.
    /// The returned future must be used, and should be spawned as a new task
    /// so it won't block the current task.
    pub fn create(
        &mut self,
        address: PathBuf,
    ) -> (
        mpsc::UnboundedSender<Incoming>,
        impl Future<Output = Result<(), std::io::Error>>,
    ) {
        let (tx, rx) = mpsc::unbounded();

        self.insert(address.clone(), tx.clone());

        (tx, ingest_data(address, rx))
    }
}

/// Given an address and `mpsc::UnboundedReceiver` handle,
/// this fn will create or open an existing file in append mode.
///
/// It will then write any incoming lines from the passed `mpsc::UnboundedReceiver`
/// to that file.
pub async fn ingest_data(
    address: PathBuf,
    mut rx: mpsc::UnboundedReceiver<Incoming>,
) -> Result<(), std::io::Error> {
    tracing::info!("Starting ingest for {:?}", address);

    let mut file = OpenOptions::new()
        .append(true)
        .create(true)
        .open(address)
        .await?;

    while let Some(incoming) = rx.next().await {
        match incoming {
            Incoming::Line(mut line) => {
                if !line.ends_with('\n') {
                    line.extend(['\n'].iter());
                }

                tracing::trace!("handling line {:?}", line);

                file.write_all(line.as_bytes()).await?;
            }
            Incoming::EOF(tx) => {
                file.flush().await?;

                let _ = tx.send(());
            }
        }
    }

    file.flush().await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempdir::TempDir;

    #[tokio::test]
    async fn test_report_senders() -> Result<(), Box<dyn std::error::Error>> {
        let tmp_dir = TempDir::new("test_report")?;
        let address = tmp_dir.path().join("test_message_1");

        let mut report_sender = ReportSenders::default();

        let (tx, fut) = report_sender.create(address.clone());

        tx.unbounded_send(Incoming::Line("foo\n".into()))?;

        report_sender
            .get(&address)
            .unwrap()
            .unbounded_send(Incoming::Line("bar".into()))?;

        tx.unbounded_send(Incoming::Line("baz\n".into()))?;

        report_sender.remove(&address);

        drop(tx);

        fut.await?;

        let contents = fs::read_to_string(&address).unwrap();

        assert_eq!(contents, "foo\nbar\nbaz\n");

        Ok(())
    }
}
