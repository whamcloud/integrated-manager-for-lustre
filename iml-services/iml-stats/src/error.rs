// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_service_queue::service_queue::ImlServiceQueueError;
use std::{error::Error, fmt};

#[derive(Debug)]
pub enum ImlStatsError {
    ImlServiceQueueError(ImlServiceQueueError),
    InfluxDbError(influx_db_client::Error),
    SystemTimeError(std::time::SystemTimeError),
}

impl fmt::Display for ImlStatsError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            ImlStatsError::ImlServiceQueueError(ref err) => write!(f, "{}", err),
            ImlStatsError::InfluxDbError(ref err) => write!(f, "{}", err),
            ImlStatsError::SystemTimeError(ref err) => write!(f, "{}", err),
        }
    }
}

impl Error for ImlStatsError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match *self {
            ImlStatsError::ImlServiceQueueError(ref err) => Some(err),
            ImlStatsError::InfluxDbError(_) => None,
            ImlStatsError::SystemTimeError(ref err) => Some(err),
        }
    }
}

impl From<ImlServiceQueueError> for ImlStatsError {
    fn from(err: ImlServiceQueueError) -> Self {
        ImlStatsError::ImlServiceQueueError(err)
    }
}

impl From<influx_db_client::Error> for ImlStatsError {
    fn from(err: influx_db_client::Error) -> Self {
        ImlStatsError::InfluxDbError(err)
    }
}

impl From<std::time::SystemTimeError> for ImlStatsError {
    fn from(err: std::time::SystemTimeError) -> Self {
        ImlStatsError::SystemTimeError(err)
    }
}
