// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! zed-enhancer -- upgrades incoming ZED events with additional information
//!
//! ZED (ZFS Event Daemon) provides changes to state in ZFS. However it is currently
//! light in the amount of information provided when state changes.
//!
//! This crate receives events from device-scanner-zedlets and may enhance them with further data
//! before passing onwards to device-scanner.

use device_types::zed::ZedCommand;
use futures::TryStreamExt;
use std::{
    convert::TryFrom,
    os::unix::{io::FromRawFd, net::UnixListener as NetUnixListener},
};
use tokio::net::UnixListener;
use tokio_net::process::Command;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use zed_enhancer::{handle_zed_commands, processor, send_to_device_scanner};

#[tokio::main(single_thread)]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let zfs_loaded = Command::new("/usr/sbin/udevadm")
        .args(&["info", "--path=/module/zfs"])
        .output()
        .await?
        .status
        .success();

    if zfs_loaded {
        tracing::debug!("Sending initial data");

        let pool_command = handle_zed_commands(ZedCommand::Init)?;

        send_to_device_scanner(pool_command).await?;
    }

    tracing::info!("Server starting");

    let addr = unsafe { NetUnixListener::from_raw_fd(3) };

    let listener = UnixListener::try_from(addr)?;

    let mut stream = listener.incoming();

    while let Some(socket) = stream.try_next().await? {
        processor(socket).await?;
    }

    Ok(())
}
