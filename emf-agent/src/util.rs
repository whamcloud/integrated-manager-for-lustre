// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use chrono::{DateTime, TimeZone, Utc};
use emf_cmd::OutputExt;
use emf_request_retry::{retry_future, RetryAction, RetryPolicy};
use futures::{future::select, FutureExt, StreamExt};
use http::StatusCode;
use lazy_static::lazy_static;
use reqwest::{header, Client};
use std::{
    fmt::Debug,
    fs::{self, File},
    io::{BufRead, BufReader},
    process::Command,
    time::Duration,
};
use tokio::{
    signal::unix::{signal, SignalKind},
    sync::mpsc::{error::SendError, unbounded_channel, UnboundedSender},
    time::interval,
};
use tokio_stream::wrappers::UnboundedReceiverStream;
use uuid::Uuid;

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

pub enum Outgoing<T> {
    ClearCache,
    Msg(T),
}

pub trait UnboundedSenderExt<T> {
    fn send_msg(&self, msg: T) -> Result<(), SendError<Outgoing<T>>>;
}

impl<T> UnboundedSenderExt<T> for UnboundedSender<Outgoing<T>> {
    fn send_msg(&self, msg: T) -> Result<(), SendError<Outgoing<T>>> {
        self.send(Outgoing::Msg(msg))
    }
}

/// Creates a writer channel that will send data to the specified port.
/// This will be picked up by the service mesh and routed to the cooresponding service.
/// All output is diffed against the previous tick. If nothing has changed, no data is sent.
#[tracing::instrument]
pub fn create_filtered_writer<T: PartialEq + Send + serde::Serialize + Sync + 'static>(
    port: u16,
) -> Result<UnboundedSender<Outgoing<T>>, EmfAgentError> {
    let (tx, rx) = unbounded_channel();
    let mut rx = UnboundedReceiverStream::new(rx);

    let client = Client::builder()
        .connect_timeout(Duration::from_secs(5))
        .http2_prior_knowledge()
        .build()?;

    let client2 = client.clone();
    let tx2 = tx.clone();

    let url = format!("http://127.0.0.1:{}", port);

    tokio::spawn(async move {
        let mut instance_id = Uuid::new_v4().to_string();

        let mut x = interval(Duration::from_secs(5));

        loop {
            x.tick().await;

            tracing::debug!("manager_service_instance_id: {}", &instance_id);

            let r = client2
                .get(&url)
                .header(header::IF_NONE_MATCH, &instance_id)
                .send()
                .await
                .and_then(|resp| resp.error_for_status());

            let r = match r {
                Ok(ref r) => r,
                Err(e) => {
                    tracing::debug!("Instance check request failed {:?}", e);

                    continue;
                }
            };

            if r.status() == StatusCode::NOT_MODIFIED {
                continue;
            }

            let server_id = match r.headers().get(header::ETAG) {
                Some(x) => x,
                None => {
                    tracing::warn!("{} not found in response", header::ETAG);

                    continue;
                }
            };

            let server_id = match server_id.to_str() {
                Ok(x) => x.to_string(),
                Err(e) => {
                    tracing::warn!(?e);

                    continue;
                }
            };

            if server_id != instance_id {
                let _ = tx2.clone().send(Outgoing::ClearCache);

                instance_id = server_id;
            }
        }
    });

    tokio::spawn(async move {
        let mut state: Option<T> = None;

        while let Some(x) = rx.next().await {
            let x = match x {
                Outgoing::ClearCache => {
                    state = None;
                    continue;
                }
                Outgoing::Msg(x) => x,
            };

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

    Ok(tx)
}

pub fn create_policy<E: Debug>() -> impl RetryPolicy<E> {
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

pub async fn wait_for_termination() {
    let mut sigterm = signal(SignalKind::terminate()).expect("Could not listen to SIGTERM");
    let mut sigint = signal(SignalKind::interrupt()).expect("Could not listen to SIGINT");

    select(sigterm.recv().boxed(), sigint.recv().boxed()).await;
}
