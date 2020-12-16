// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    error,
    reducers::{mount::update_mount, udev::update_udev},
    state,
};
use device_types::{state::State, Command};
use futures::{
    channel::mpsc::UnboundedReceiver, channel::mpsc::UnboundedSender, future::join_all, StreamExt,
    TryStreamExt,
};
use tokio::{
    io::AsyncWriteExt,
    net::{UnixListener, UnixStream},
};
use tokio_util::codec::{FramedRead, LinesCodec};

pub enum WriterCmd {
    Add(UnixStream),
    Msg(bytes::Bytes),
}

fn is_error(xs: &[Result<(), std::io::Error>], idx: usize) -> bool {
    if let Err(e) = &xs[idx] {
        tracing::debug!("Error writing to client {}. Removing client", e);

        false
    } else {
        true
    }
}

pub async fn writer(mut rx: UnboundedReceiver<WriterCmd>) {
    let mut writers = vec![];

    while let Some(cmd) = rx.next().await {
        match cmd {
            WriterCmd::Add(w) => writers.push(w),
            WriterCmd::Msg(x) => {
                tracing::trace!("Starting write to all clients");

                let xs = join_all(writers.iter_mut().map(|writer| writer.write_all(&x))).await;

                writers = writers
                    .into_iter()
                    .enumerate()
                    .filter(|(idx, _)| is_error(&xs, *idx))
                    .map(|(_, w)| w)
                    .collect();

                tracing::trace!("{} clients remain.", writers.len());
            }
        }
    }
}

pub async fn reader(
    mut listener: UnixListener,
    tx: UnboundedSender<WriterCmd>,
) -> Result<(), error::Error> {
    let mut state = State::new();

    while let Some(sock) = listener.try_next().await? {
        tracing::debug!("Client connected");

        let (x, sock) = FramedRead::new(sock, LinesCodec::new()).into_future().await;

        let mut sock = sock.into_inner();

        if let Some(x) = x {
            let cmd = serde_json::from_str::<Command>(x?.trim_end())?;

            tracing::debug!("Incoming Command: {:?}", cmd);

            match cmd {
                Command::Stream => {
                    let output = state::produce_device_graph(&state)?;

                    sock.write_all(&output).await?;

                    tx.unbounded_send(WriterCmd::Add(sock))?;

                    continue;
                }
                Command::GetMounts => {
                    let v = serde_json::to_string(&state.local_mounts)?;
                    let b = bytes::BytesMut::from((v + "\n").as_str());
                    let b = b.freeze();

                    sock.shutdown(std::net::Shutdown::Read)?;

                    sock.write_all(&b).await?;

                    continue;
                }
                Command::UdevCommand(x) => {
                    sock.shutdown(std::net::Shutdown::Both)?;

                    state.uevents = update_udev(&state.uevents, x);
                }
                Command::MountCommand(x) => {
                    sock.shutdown(std::net::Shutdown::Both)?;

                    state.local_mounts = update_mount(state.local_mounts, x);
                }
            };

            let output = state::produce_device_graph(&state)?;

            tx.unbounded_send(WriterCmd::Msg(output))?;

            tracing::debug!("sent new output");
        }
    }

    Ok(())
}
