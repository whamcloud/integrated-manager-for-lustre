// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_service_queue::service_queue::ImlServiceQueueError;

#[derive(Debug)]
pub enum ImlDevicesError {
    TokioPostgresError(iml_postgres::Error),
    ImlServiceQueueError(ImlServiceQueueError),
}

impl std::fmt::Display for ImlDevicesError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlDevicesError::TokioPostgresError(ref err) => write!(f, "{}", err),
            ImlDevicesError::ImlServiceQueueError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlDevicesError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlDevicesError::TokioPostgresError(ref err) => Some(err),
            ImlDevicesError::ImlServiceQueueError(ref err) => Some(err),
        }
    }
}

impl From<iml_postgres::Error> for ImlDevicesError {
    fn from(err: iml_postgres::Error) -> Self {
        ImlDevicesError::TokioPostgresError(err)
    }
}

impl From<ImlServiceQueueError> for ImlDevicesError {
    fn from(err: ImlServiceQueueError) -> Self {
        ImlDevicesError::ImlServiceQueueError(err)
    }
}
