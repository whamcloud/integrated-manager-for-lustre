// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use device_types::mount::Mount;
use futures::{Stream, StreamExt, TryFutureExt, TryStreamExt};
use tokio::{io::AsyncWriteExt, net::UnixStream};
use tokio_util::codec::{FramedRead, LinesCodec};

pub async fn connect() -> Result<UnixStream, EmfAgentError> {
    let x = UnixStream::connect("/var/run/device-scanner.sock").await?;

    Ok(x)
}

pub enum Cmd {
    Stream,
    GetMounts,
}

impl From<Cmd> for &[u8] {
    fn from(cmd: Cmd) -> Self {
        match cmd {
            Cmd::Stream => b"\"Stream\"\n",
            Cmd::GetMounts => b"\"GetMounts\"\n",
        }
    }
}

pub fn stream_lines(
    cmd: impl Into<&'static [u8]>,
) -> impl Stream<Item = Result<String, EmfAgentError>> {
    connect()
        .and_then(|mut conn| async {
            conn.write_all(cmd.into())
                .err_into::<EmfAgentError>()
                .await?;

            Ok(conn)
        })
        .map_ok(|c| FramedRead::new(c, LinesCodec::new()).err_into())
        .try_flatten_stream()
}

pub async fn get_mounts() -> Result<Vec<Mount>, EmfAgentError> {
    let (x, _) = stream_lines(Cmd::GetMounts).boxed().into_future().await;

    let x = match x {
        Some(x) => serde_json::from_str(x?.as_str())?,
        None => vec![],
    };

    Ok(x)
}

pub async fn get_snapshot_mounts() -> Result<Vec<Mount>, EmfAgentError> {
    let xs = get_mounts()
        .await?
        .into_iter()
        .filter(|x| x.opts.0.split(',').any(|x| x == "nomgs"))
        .filter(|x| x.fs_type.0 == "lustre")
        .collect::<Vec<Mount>>();

    Ok(xs)
}
