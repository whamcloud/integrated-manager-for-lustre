// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod command;
pub mod graph;
mod job;
mod snapshot;
mod step;

pub use command::{run_command, run_jobs, JobStates};
use futures::future::Aborted;

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error(transparent)]
    Aborted(#[from] Aborted),
    #[error("State Not Found")]
    NotFound,
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
    #[error(transparent)]
    ImlActionClientError(#[from] iml_action_client::ImlActionClientError),
    #[error(transparent)]
    SqlxError(#[from] iml_postgres::sqlx::Error),
}
