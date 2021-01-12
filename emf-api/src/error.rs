// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_job_scheduler_rpc::EmfJobSchedulerRpcError;
use emf_manager_client::EmfManagerClientError;
use emf_postgres::sqlx;
use emf_rabbit::{self, EmfRabbitError};
use futures::channel::oneshot;
use thiserror::Error;
use warp::reject;

#[derive(Debug, Error)]
pub enum EmfApiError {
    #[error(transparent)]
    EmfJobSchedulerRpcError(#[from] EmfJobSchedulerRpcError),
    #[error(transparent)]
    EmfRabbitError(#[from] EmfRabbitError),
    #[error(transparent)]
    EmfManagerClientError(#[from] EmfManagerClientError),
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
}

impl reject::Reject for EmfApiError {}

impl From<EmfApiError> for warp::Rejection {
    fn from(err: EmfApiError) -> Self {
        warp::reject::custom(err)
    }
}
