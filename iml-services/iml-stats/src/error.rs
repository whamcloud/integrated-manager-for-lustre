// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_service_queue::service_queue::ImlServiceQueueError;
use std::{error::Error, fmt};

#[derive(Debug)]
pub enum ImlStatsError {
    ImlServiceQueueError(ImlServiceQueueError),
    InfluxDbError(influxdb::Error),
}

impl fmt::Display for ImlStatsError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            ImlStatsError::ImlServiceQueueError(ref err) => write!(f, "{}", err),
            ImlStatsError::InfluxDbError(ref err) => write!(f, "{}", err),
        }
    }
}

impl Error for ImlStatsError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match *self {
            ImlStatsError::ImlServiceQueueError(ref err) => Some(err),
            ImlStatsError::InfluxDbError(_) => None,
        }
    }
}

impl From<ImlServiceQueueError> for ImlStatsError {
    fn from(err: ImlServiceQueueError) -> Self {
        ImlStatsError::ImlServiceQueueError(err)
    }
}

impl From<influxdb::Error> for ImlStatsError {
    fn from(err: influxdb::Error) -> Self {
        ImlStatsError::InfluxDbError(err)
    }
}
