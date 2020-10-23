// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_service_queue::service_queue::ImlServiceQueueError;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ImlStatsError {
    #[error(transparent)]
    ImlServiceQueueError(#[from] ImlServiceQueueError),
    #[error(transparent)]
    ImlInfluxError(#[from] iml_influx::Error),
    #[error(transparent)]
    SystemTimeError(#[from] std::time::SystemTimeError),
    #[error(transparent)]
    ImlRabbitError(#[from] iml_rabbit::ImlRabbitError),
}
