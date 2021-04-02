// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! #NetworkIB daemon-plugin
//!
//! This module is responsible for continually fetching the Infiniband network interfaces and their respective stats.
//!
//!

use emf_agent::{
    agent_error::EmfAgentError,
    env,
    util::{create_filtered_writer, UnboundedSenderExt},
};
use emf_wire_types::IBInterface;
use futures::{Stream, TryFutureExt, TryStreamExt};
use std::{path::PathBuf, time::Duration};
use tokio::{fs, time::interval};
use tokio_stream::wrappers::ReadDirStream;

async fn get_ib_name() -> Result<impl Stream<Item = Result<PathBuf, EmfAgentError>>, EmfAgentError>
{
    let s = tokio::fs::read_dir("/sys/class/infiniband/")
        .map_ok(ReadDirStream::new)
        .await?
        .err_into()
        .map_ok(|d| d.path());

    Ok(s)
}

async fn get_stats_path(path: &PathBuf) -> Result<Option<IBInterface>, EmfAgentError> {
    let interface = path
        .file_name()
        .and_then(|x| x.to_str())
        .map(|x| x.to_string());

    let interface = match interface {
        Some(x) => x,
        None => return Ok(None),
    };

    let contents_rcv_data = fs::read_to_string(path.join("ports/1/counters/port_rcv_data")).await?;
    let contents_rcv_data = contents_rcv_data.trim();

    let contents_xmit_data =
        fs::read_to_string(path.join("ports/1/counters/port_xmit_data")).await?;
    let contents_xmit_data = contents_xmit_data.trim();

    Ok(Some(IBInterface {
        interface,
        rcv_byte_total: contents_rcv_data.to_string().parse::<u64>()?,
        xmit_byte_total: contents_xmit_data.to_string().parse::<u64>()?,
    }))
}

async fn get_ib_stats(
) -> Result<impl Stream<Item = Result<IBInterface, EmfAgentError>>, EmfAgentError> {
    let s = get_ib_name().await?.try_filter_map(|x| async move {
        let x = get_stats_path(&x).await?;

        Ok(x)
    });

    Ok(s)
}

async fn get_ib_network_interfaces() -> Vec<IBInterface> {
    match get_ib_stats().await {
        Ok(xs) => match xs.try_collect().await {
            Ok(xs) => xs,
            Err(e) => {
                tracing::error!("Unable to find IB metrics, try_collect error: {:?}", e);
                return vec![];
            }
        },
        Err(e) => {
            tracing::error!("Unable to find IB metrics, error: {:?}", e);
            return vec![];
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), EmfAgentError> {
    emf_tracing::init();

    let mut x = interval(Duration::from_secs(10));

    let port = env::get_port("NETWORK_IB_AGENT_NETWORK_SERVICE_PORT");

    let writer = create_filtered_writer::<Vec<IBInterface>>(port)?;

    loop {
        x.tick().await;

        let x = get_ib_network_interfaces().await;

        let _ = writer.send_msg(x);
    }
}
