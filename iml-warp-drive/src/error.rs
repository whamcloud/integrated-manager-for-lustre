// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_client::ImlManagerClientError;
use iml_postgres::DbError;
use iml_rabbit::ImlRabbitError;
use warp::reject;

#[derive(Debug, thiserror::Error)]
pub enum ImlWarpDriveError {
    #[error(transparent)]
    ImlRabbitError(#[from] ImlRabbitError),
    #[error(transparent)]
    ImlManagerClientError(#[from] ImlManagerClientError),
    #[error(transparent)]
    StateMachineError(#[from] iml_state_machine::Error),
    #[error(transparent)]
    TokioPostgresError(#[from] iml_postgres::Error),
    #[error(transparent)]
    DbError(Box<DbError>),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::error::Error),
}

impl reject::Reject for ImlWarpDriveError {}

impl From<DbError> for ImlWarpDriveError {
    fn from(err: DbError) -> Self {
        ImlWarpDriveError::DbError(Box::new(err))
    }
}
