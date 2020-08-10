// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum ImlTaskRunnerError {
    #[error(transparent)]
    ImlPgError(#[from] iml_postgres::Error),
    #[error(transparent)]
    JsonError(#[from] serde_json::Error),
    #[error(transparent)]
    ImlPgPoolError(#[from] iml_postgres::sqlx::Error),
}
