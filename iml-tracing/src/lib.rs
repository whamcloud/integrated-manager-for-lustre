// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use tokio::signal::unix::{signal, SignalKind};
pub use tracing;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

/// Initialize logging by reading the `RUST_LOG` environment variable.
/// In addition, setup signal handlers
///
/// - `SIGUSR1` will set log level to info.
/// - `SIGUSR2` will set log level to debug.
pub fn init() {
    let builder = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .with_filter_reloading();

    let handle = builder.reload_handle();
    builder.try_init().expect("Could not init builder");

    let handle2 = handle.clone();

    tokio::spawn(async move {
        let mut stream = signal(SignalKind::user_defined1()).expect("Could not listen to SIGUSR1");

        while stream.recv().await.is_some() {
            handle2.reload("info").unwrap();
        }
    });

    tokio::spawn(async move {
        let mut stream = signal(SignalKind::user_defined2()).expect("Could not listen to SIGUSR2");

        while stream.recv().await.is_some() {
            handle.reload("debug").unwrap();
        }
    });
}
