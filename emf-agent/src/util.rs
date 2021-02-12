// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use chrono::{DateTime, TimeZone, Utc};
use emf_cmd::OutputExt;
use emf_request_retry::{retry_future, RetryAction, RetryPolicy};
use futures::{future::select, FutureExt, StreamExt};
use lazy_static::lazy_static;
use reqwest::Client;
use std::{
    fmt::Debug,
    fs::{self, File},
    io::{BufRead, BufReader},
    process::Command,
    time::Duration,
};
use tokio::{
    signal::unix::{signal, SignalKind},
    sync::mpsc::{unbounded_channel, UnboundedSender},
};
use tokio_stream::wrappers::UnboundedReceiverStream;

lazy_static! {
    /// Gets the FQDN or panics
    pub static ref FQDN: String = {
        let output = Command::new("hostname")
        .arg("--fqdn")
        .output()
        .unwrap();

        if !output.status.success() {
            panic!("Could not lookup FQDN {}", output.stderr_string_lossy());
        }

        let x = output.stdout_string_lossy();

        x.trim().to_string()
    };
}

lazy_static! {
    // Gets the server boot time or panics.
    pub static ref BOOT_TIME: DateTime<Utc> = {
        let input = File::open("/proc/stat").expect("Could not open /proc/stat");
        let buffered = BufReader::new(input);

        let lines = buffered
            .lines()
            .collect::<std::result::Result<Vec<String>, _>>()
            .expect("Error reading lines from /proc/stat");

        let secs = lines
            .iter()
            .map(|l| l.split_whitespace().collect())
            .filter_map(|xs: Vec<&str>| match xs[..2] {
                ["btime", v] => Some(v),
                _ => None,
            })
            .next()
            .expect("Could not find boot time")
            .parse()
            .expect("Could not parse boot secs into int");

        Utc.timestamp(secs, 0)
    };
}

lazy_static! {
    /// Gets the machine-id or panics
    pub static ref MACHINE_ID: String = {
        let machine_id =
            fs::read_to_string("/etc/machine-id").expect("Could not read /etc/machine-id");

        machine_id.trim().to_string()
    };
}

fn create_policy<E: Debug>() -> impl RetryPolicy<E> {
    |k: u32, e| match k {
        0 => RetryAction::RetryNow,
        k if k < 5 => {
            let secs = (2 * k) as u64;

            tracing::debug!(
                "Waiting {} seconds for outbound port to become available...",
                secs
            );

            RetryAction::WaitFor(Duration::from_secs(secs))
        }
        _ => RetryAction::ReturnError(e),
    }
}

/// Creates a writer channel that will send data to the specified port.
/// This will be picked up by the service mesh and routed to the cooresponding service.
/// All output is diffed against the previous tick. If nothing has changed, no data is sent.
#[tracing::instrument]
pub fn create_filtered_writer<T: PartialEq + Send + serde::Serialize + Sync + 'static>(
    port: u16,
) -> UnboundedSender<T> {
    let (tx, rx) = unbounded_channel();
    let mut rx = UnboundedReceiverStream::new(rx);

    tokio::spawn(async move {
        let mut state: Option<T> = None;

        let client = Client::builder()
            .connect_timeout(Duration::from_secs(5))
            .http2_prior_knowledge()
            .build()?;

        while let Some(x) = rx.next().await {
            let same = Some(&x) == state.as_ref();

            if !same {
                let policy = create_policy();

                let client = client.clone();

                let r = retry_future(
                    |_| {
                        client
                            .post(&format!("http://127.0.0.1:{}", port))
                            .json(&(FQDN.as_str(), &x))
                            .send()
                    },
                    policy,
                )
                .await
                .and_then(|resp| resp.error_for_status());

                if r.is_ok() {
                    state.replace(x);
                } else {
                    tracing::debug!("Send failed, uninitializing cache");

                    state = None;
                }
            }
        }

        Ok::<_, EmfAgentError>(())
    });

    tx
}

pub async fn wait_for_termination() {
    let mut sigterm = signal(SignalKind::terminate()).expect("Could not listen to SIGTERM");
    let mut sigint = signal(SignalKind::interrupt()).expect("Could not listen to SIGINT");

    select(sigterm.recv().boxed(), sigint.recv().boxed()).await;
}
