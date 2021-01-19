// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_manager_client::EmfManagerClientError;
use emf_postgres::DbError;
use emf_rabbit::EmfRabbitError;
use warp::reject;

#[derive(Debug)]
pub enum EmfWarpDriveError {
    EmfRabbitError(EmfRabbitError),
    EmfManagerClientError(EmfManagerClientError),
    TokioPostgresError(emf_postgres::Error),
    DbError(Box<DbError>),
    SerdeJsonError(serde_json::error::Error),
}

impl reject::Reject for EmfWarpDriveError {}

impl std::fmt::Display for EmfWarpDriveError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            EmfWarpDriveError::EmfRabbitError(ref err) => write!(f, "{}", err),
            EmfWarpDriveError::EmfManagerClientError(ref err) => write!(f, "{}", err),
            EmfWarpDriveError::TokioPostgresError(ref err) => write!(f, "{}", err),
            EmfWarpDriveError::DbError(ref err) => write!(f, "{}", err),
            EmfWarpDriveError::SerdeJsonError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for EmfWarpDriveError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            EmfWarpDriveError::EmfRabbitError(ref err) => Some(err),
            EmfWarpDriveError::EmfManagerClientError(ref err) => Some(err),
            EmfWarpDriveError::TokioPostgresError(ref err) => Some(err),
            EmfWarpDriveError::DbError(ref err) => Some(err),
            EmfWarpDriveError::SerdeJsonError(ref err) => Some(err),
        }
    }
}

impl From<EmfRabbitError> for EmfWarpDriveError {
    fn from(err: EmfRabbitError) -> Self {
        EmfWarpDriveError::EmfRabbitError(err)
    }
}

impl From<EmfManagerClientError> for EmfWarpDriveError {
    fn from(err: EmfManagerClientError) -> Self {
        EmfWarpDriveError::EmfManagerClientError(err)
    }
}

impl From<DbError> for EmfWarpDriveError {
    fn from(err: DbError) -> Self {
        EmfWarpDriveError::DbError(Box::new(err))
    }
}

impl From<emf_postgres::Error> for EmfWarpDriveError {
    fn from(err: emf_postgres::Error) -> Self {
        EmfWarpDriveError::TokioPostgresError(err)
    }
}

impl From<serde_json::error::Error> for EmfWarpDriveError {
    fn from(err: serde_json::error::Error) -> Self {
        EmfWarpDriveError::SerdeJsonError(err)
    }
}
