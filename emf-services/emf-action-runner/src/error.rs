// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_postgres::sqlx;
use emf_wire_types::Fqdn;
use futures::channel::oneshot;
use std::fmt;
use thiserror::Error;
use tokio::time;
use warp::reject;

#[derive(Debug)]
pub struct RequiredError(pub String);

impl fmt::Display for RequiredError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{:?}", self.0)
    }
}

impl std::error::Error for RequiredError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

/// Encapsulates any errors that may happen while working with the `ActionRunner` service
#[derive(Debug, Error)]
pub enum ActionRunnerError {
    #[error("Fqdn not found in sessions: {0}")]
    AwaitSession(Fqdn),
    #[error(transparent)]
    TokioTimerError(#[from] time::Error),
    #[error(transparent)]
    EmfRabbitError(#[from] emf_rabbit::EmfRabbitError),
    #[error(transparent)]
    OneShotCanceledError(#[from] oneshot::Canceled),
    #[error(transparent)]
    RequiredError(#[from] RequiredError),
    #[error(transparent)]
    SqlxError(#[from] sqlx::Error),
}

impl reject::Reject for ActionRunnerError {}
