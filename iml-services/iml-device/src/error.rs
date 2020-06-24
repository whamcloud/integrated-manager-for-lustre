// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_orm::{tokio_diesel::AsyncError, ImlOrmError};
use iml_service_queue::service_queue::ImlServiceQueueError;
use thiserror::Error;
use warp::reject;

#[derive(Error, Debug)]
pub enum ImlDeviceError {
    #[error(transparent)]
    AsyncError(#[from] AsyncError),
    #[error(transparent)]
    ImlOrmError(#[from] ImlOrmError),
    #[error(transparent)]
    ImlServiceQueueError(#[from] ImlServiceQueueError),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
    #[error(transparent)]
    ImlRabbitError(#[from] iml_rabbit::ImlRabbitError),
}

impl reject::Reject for ImlDeviceError {}
