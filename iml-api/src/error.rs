// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::channel::oneshot;
use iml_action_client::ImlActionClientError;
use iml_job_scheduler_rpc::ImlJobSchedulerRpcError;
use iml_postgres::sqlx;
use iml_rabbit::{self, ImlRabbitError};
use thiserror::Error;
use warp::reject;

#[derive(Debug, Error)]
pub enum ImlApiError {
    #[error(transparent)]
    ImlActionClientError(#[from] ImlActionClientError),
    #[error(transparent)]
    ImlJobSchedulerRpcError(#[from] ImlJobSchedulerRpcError),
    #[error(transparent)]
    ImlRabbitError(#[from] ImlRabbitError),
    #[error("Not Found")]
    NoneError,
    #[error(transparent)]
    OneshotCanceled(#[from] oneshot::Canceled),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::error::Error),
    #[error(transparent)]
    SqlxError(#[from] sqlx::Error),
}

impl reject::Reject for ImlApiError {}

impl From<ImlApiError> for warp::Rejection {
    fn from(err: ImlApiError) -> Self {
        warp::reject::custom(err)
    }
}
