// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_client::ImlManagerClientError;
use iml_postgres::DbError;
use iml_rabbit::ImlRabbitError;
use warp::reject;

#[derive(Debug)]
pub enum ImlWarpDriveError {
    ImlRabbitError(ImlRabbitError),
    ImlManagerClientError(ImlManagerClientError),
    TokioPostgresError(iml_postgres::Error),
    DbError(DbError),
    SerdeJsonError(serde_json::error::Error),
}

impl reject::Reject for ImlWarpDriveError {}

impl std::fmt::Display for ImlWarpDriveError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlWarpDriveError::ImlRabbitError(ref err) => write!(f, "{}", err),
            ImlWarpDriveError::ImlManagerClientError(ref err) => write!(f, "{}", err),
            ImlWarpDriveError::TokioPostgresError(ref err) => write!(f, "{}", err),
            ImlWarpDriveError::DbError(ref err) => write!(f, "{}", err),
            ImlWarpDriveError::SerdeJsonError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlWarpDriveError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlWarpDriveError::ImlRabbitError(ref err) => Some(err),
            ImlWarpDriveError::ImlManagerClientError(ref err) => Some(err),
            ImlWarpDriveError::TokioPostgresError(ref err) => Some(err),
            ImlWarpDriveError::DbError(ref err) => Some(err),
            ImlWarpDriveError::SerdeJsonError(ref err) => Some(err),
        }
    }
}

impl From<ImlRabbitError> for ImlWarpDriveError {
    fn from(err: ImlRabbitError) -> Self {
        ImlWarpDriveError::ImlRabbitError(err)
    }
}

impl From<ImlManagerClientError> for ImlWarpDriveError {
    fn from(err: ImlManagerClientError) -> Self {
        ImlWarpDriveError::ImlManagerClientError(err)
    }
}

impl From<DbError> for ImlWarpDriveError {
    fn from(err: DbError) -> Self {
        ImlWarpDriveError::DbError(err)
    }
}

impl From<iml_postgres::Error> for ImlWarpDriveError {
    fn from(err: iml_postgres::Error) -> Self {
        ImlWarpDriveError::TokioPostgresError(err)
    }
}

impl From<serde_json::error::Error> for ImlWarpDriveError {
    fn from(err: serde_json::error::Error) -> Self {
        ImlWarpDriveError::SerdeJsonError(err)
    }
}
