// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum EmfTaskRunnerError {
    #[error(transparent)]
    JsonError(#[from] serde_json::Error),
    #[error(transparent)]
    SqlxError(#[from] sqlx::Error),
}
