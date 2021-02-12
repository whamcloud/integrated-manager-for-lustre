// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use thiserror::Error;

#[derive(Error, Debug)]
pub enum EmfDeviceError {
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
    #[error(transparent)]
    SqlxCoreError(#[from] sqlx::Error),
    #[error(transparent)]
    SqlxMigrateError(#[from] sqlx::migrate::MigrateError),
    #[error("Could not find index in target name {0}")]
    TargetIndexNotFoundError(String),
}
