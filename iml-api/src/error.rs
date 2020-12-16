// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::channel::oneshot;
use iml_job_scheduler_rpc::ImlJobSchedulerRpcError;
use iml_manager_client::ImlManagerClientError;
use iml_postgres::sqlx;
use iml_rabbit::{self, ImlRabbitError};
use thiserror::Error;
use warp::reject;

#[derive(Debug, Error)]
pub enum ImlApiError {
    #[error(transparent)]
    ImlJobSchedulerRpcError(#[from] ImlJobSchedulerRpcError),
    #[error(transparent)]
    ImlRabbitError(#[from] ImlRabbitError),
    #[error(transparent)]
    ImlManagerClientError(#[from] ImlManagerClientError),
    #[error("Not Found")]
    NoneError,
    #[error(transparent)]
    OneshotCanceled(#[from] oneshot::Canceled),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::error::Error),
    #[error(transparent)]
    SqlxError(#[from] sqlx::Error),
    #[error("Filesystem Not Found")]
    FilesystemNotFound,
    #[error("Filesystem Not Found")]
    MgsNotFound,
    #[error(transparent)]
    Utf8Error(#[from] std::str::Utf8Error),
    #[error("No session id")]
    NoSessionId,
}

impl reject::Reject for ImlApiError {}

impl From<ImlApiError> for warp::Rejection {
    fn from(err: ImlApiError) -> Self {
        warp::reject::custom(err)
    }
}
