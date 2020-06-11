// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum ImlTaskRunnerError {
    #[error(transparent)]
    AsyncError(#[from] iml_orm::tokio_diesel::AsyncError),
    #[error(transparent)]
    R2D2Error(#[from] iml_orm::r2d2::Error),
    #[error(transparent)]
    ImlPgError(#[from] iml_postgres::Error),
    #[error(transparent)]
    JsonError(#[from] serde_json::Error),
    #[error(transparent)]
    ImlPgConfigError(#[from] iml_postgres::pool::ConfigError),
    #[error(transparent)]
    ImlPgPoolError(#[from] iml_postgres::pool::PoolError),
}
