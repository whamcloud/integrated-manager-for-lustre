// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_scanner_daemon::daemon;
use futures::channel::mpsc;
use std::{
    convert::TryFrom,
    os::unix::{io::FromRawFd, net::UnixListener as NetUnixListener},
};
use tokio::net::UnixListener;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    tracing::info!("Server starting");

    let addr = unsafe { NetUnixListener::from_raw_fd(3) };

    let listener = UnixListener::try_from(addr)?;

    let (tx, rx) = mpsc::unbounded();

    tokio::spawn(daemon::writer(rx));

    daemon::reader(listener, tx).await?;

    Ok(())
}
