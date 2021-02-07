// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use thiserror::Error;
use warp::reject;

#[derive(Debug, Error)]
pub enum EmfWarpDriveError {
    #[error(transparent)]
    EmfPgPoolError(#[from] emf_postgres::sqlx::Error),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::error::Error),
}

impl reject::Reject for EmfWarpDriveError {}
