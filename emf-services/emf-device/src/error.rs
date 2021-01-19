// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_postgres::sqlx;
use emf_service_queue::service_queue::EmfServiceQueueError;
use thiserror::Error;
use warp::reject;

#[derive(Error, Debug)]
pub enum EmfDeviceError {
    #[error(transparent)]
    EmfRabbitError(#[from] emf_rabbit::EmfRabbitError),
    #[error(transparent)]
    EmfServiceQueueError(#[from] EmfServiceQueueError),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
    #[error(transparent)]
    SqlxCoreError(#[from] sqlx::Error),
    #[error(transparent)]
    SqlxMigrateError(#[from] sqlx::migrate::MigrateError),
}

impl reject::Reject for EmfDeviceError {}
