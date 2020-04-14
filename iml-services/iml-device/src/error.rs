// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_service_queue::service_queue::ImlServiceQueueError;
use thiserror::Error;
use tokio_postgres;
use warp::reject;

#[derive(Error, Debug)]
pub enum ImlDeviceError {
    #[error(transparent)]
    ImlServiceQueueError(#[from] ImlServiceQueueError),
    #[error(transparent)]
    TokioPostgresError(#[from] tokio_postgres::error::Error),
    #[error(transparent)]
    SerdeError(#[from] serde_json::error::Error),
}

impl reject::Reject for ImlDeviceError {}
