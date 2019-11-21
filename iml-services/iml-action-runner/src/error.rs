// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::channel::oneshot;
use iml_wire_types::Fqdn;
use tokio::timer;
use warp::reject;

/// Encapsulates any errors that may happen while working with the `ActionRunner` service
#[derive(Debug)]
pub enum ActionRunnerError {
    AwaitSession(Fqdn),
    TokioTimerError(timer::Error),
    ImlRabbitError(iml_rabbit::ImlRabbitError),
    OneShotCanceledError(oneshot::Canceled),
}

impl reject::Reject for ActionRunnerError {}

impl std::fmt::Display for ActionRunnerError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ActionRunnerError::AwaitSession(ref err) => {
                write!(f, "Fqdn not found in sessions: {}", err)
            }
            ActionRunnerError::TokioTimerError(ref err) => write!(f, "{}", err),
            ActionRunnerError::ImlRabbitError(ref err) => write!(f, "{}", err),
            ActionRunnerError::OneShotCanceledError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ActionRunnerError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ActionRunnerError::AwaitSession(_) => None,
            ActionRunnerError::TokioTimerError(ref err) => Some(err),
            ActionRunnerError::ImlRabbitError(ref err) => Some(err),
            ActionRunnerError::OneShotCanceledError(ref err) => Some(err),
        }
    }
}

impl From<timer::Error> for ActionRunnerError {
    fn from(err: timer::Error) -> Self {
        ActionRunnerError::TokioTimerError(err)
    }
}

impl From<iml_rabbit::ImlRabbitError> for ActionRunnerError {
    fn from(err: iml_rabbit::ImlRabbitError) -> Self {
        ActionRunnerError::ImlRabbitError(err)
    }
}

impl From<oneshot::Canceled> for ActionRunnerError {
    fn from(err: oneshot::Canceled) -> Self {
        ActionRunnerError::OneShotCanceledError(err)
    }
}
