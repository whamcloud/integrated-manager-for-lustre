// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Iml Job Scheduler RPC client
//!
//! This module provides a client to make rpc calls to the `job_scheduler`.
//!
//! It should be able to call into the job scheduler and recieve results the same as `job_scheduler_client`.

mod request;
mod response;

use iml_rabbit::{
    basic_consume_one, basic_publish, bind_queue, close_channel, create_channel, declare_queue,
    declare_transient_exchange, BasicConsumeOptions, Connection, ExchangeKind, ImlRabbitError,
    QueueDeclareOptions,
};
use iml_wire_types::CompositeId;
use request::Request;
use response::Response;
use std::{collections::HashMap, fmt::Debug};
use uuid::Uuid;

static JOB_SCHEDULER_RPC: &str = "JobSchedulerRpc";
static RPC: &str = "rpc";

#[derive(Debug)]
pub enum ImlJobSchedulerRpcError {
    ImlRabbitError(ImlRabbitError),
    RpcError(String),
    SerdeJsonError(serde_json::error::Error),
}

impl std::fmt::Display for ImlJobSchedulerRpcError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlJobSchedulerRpcError::ImlRabbitError(ref err) => write!(f, "{}", err),
            ImlJobSchedulerRpcError::RpcError(ref err) => write!(f, "{}", err),
            ImlJobSchedulerRpcError::SerdeJsonError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlJobSchedulerRpcError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlJobSchedulerRpcError::ImlRabbitError(ref err) => Some(err),
            ImlJobSchedulerRpcError::RpcError(_) => None,
            ImlJobSchedulerRpcError::SerdeJsonError(ref err) => Some(err),
        }
    }
}

impl From<ImlRabbitError> for ImlJobSchedulerRpcError {
    fn from(err: ImlRabbitError) -> Self {
        ImlJobSchedulerRpcError::ImlRabbitError(err)
    }
}

impl From<String> for ImlJobSchedulerRpcError {
    fn from(err: String) -> Self {
        ImlJobSchedulerRpcError::RpcError(err)
    }
}

impl From<serde_json::error::Error> for ImlJobSchedulerRpcError {
    fn from(err: serde_json::error::Error) -> Self {
        ImlJobSchedulerRpcError::SerdeJsonError(err)
    }
}

/// Performs an RPC call to the `job_scheduler`.
pub async fn call<I: Debug + serde::Serialize, T: serde::de::DeserializeOwned>(
    conn: &Connection,
    method: impl Into<String>,
    args: impl Into<Option<Vec<I>>>,
    kwargs: impl Into<Option<HashMap<String, String>>>,
) -> Result<T, ImlJobSchedulerRpcError> {
    let response_key = format!(
        "{}.responses_{}",
        JOB_SCHEDULER_RPC,
        Uuid::new_v4().to_hyphenated().to_string()
    );

    let method = method.into();

    let req = Request::new(
        &method,
        &response_key,
        args.into().unwrap_or_default(),
        kwargs.into().unwrap_or_default(),
    );

    tracing::debug!("--> to job scheduler {} {:?}", method, req);

    let channel = create_channel(conn).await?;
    declare_transient_exchange(&channel, RPC, ExchangeKind::Topic).await?;

    let queue = declare_queue(
        &channel,
        &response_key,
        QueueDeclareOptions {
            durable: false,
            auto_delete: true,
            ..QueueDeclareOptions::default()
        },
        None,
    )
    .await?;

    bind_queue(&channel, RPC, &response_key, &response_key).await?;

    basic_publish(
        &channel,
        RPC,
        format!("{}.requests", JOB_SCHEDULER_RPC),
        req,
    )
    .await?;

    let (channel, delivery) = basic_consume_one(
        &channel,
        queue,
        &response_key,
        Some(BasicConsumeOptions {
            no_ack: true,
            ..BasicConsumeOptions::default()
        }),
    )
    .await?;

    tracing::debug!(
        "<- from job scheduler {} {:?}",
        method,
        std::str::from_utf8(&delivery.data)
    );

    close_channel(&channel).await?;

    let resp: Response<T> = serde_json::from_slice(&delivery.data)?;

    if let Some(e) = resp.exception {
        return Err(e.into());
    }

    resp.result.ok_or_else(|| {
        ImlJobSchedulerRpcError::RpcError("RPC response was unexpectedly empty".into())
    })
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct Transition {
    pub display_group: u64,
    pub display_order: u64,
    pub long_description: String,
    pub state: String,
    pub verb: String,
}

pub async fn available_transitions(
    conn: &Connection,
    ids: &[CompositeId],
) -> Result<HashMap<CompositeId, Vec<Transition>>, ImlJobSchedulerRpcError> {
    let ids: Vec<_> = ids.iter().map(|x| (x.0, x.1)).collect();

    call(conn, "available_transitions", vec![ids], None).await
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct Job {
    pub args: Option<HashMap<String, Option<u64>>>,
    pub class_name: Option<String>,
    pub confirmation: Option<String>,
    pub display_group: u64,
    pub display_order: u64,
    pub long_description: String,
    pub verb: String,
}

pub async fn available_jobs(
    client: &Connection,
    ids: &[CompositeId],
) -> Result<HashMap<CompositeId, Vec<Job>>, ImlJobSchedulerRpcError> {
    let ids: Vec<_> = ids.iter().map(|x| (x.0, x.1)).collect();

    call(client, "available_jobs", vec![ids], None).await
}
