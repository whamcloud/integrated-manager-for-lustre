// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_rabbit::EmfRabbitError;
use futures::channel::oneshot;
use warp::reject;

#[derive(Debug)]
pub enum EmfAgentCommsError {
    EmfRabbitError(EmfRabbitError),
    SerdeJsonError(serde_json::error::Error),
    OneshotCanceled(oneshot::Canceled),
}

impl reject::Reject for EmfAgentCommsError {}

impl std::fmt::Display for EmfAgentCommsError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            EmfAgentCommsError::EmfRabbitError(ref err) => write!(f, "{}", err),
            EmfAgentCommsError::SerdeJsonError(ref err) => write!(f, "{}", err),
            EmfAgentCommsError::OneshotCanceled(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for EmfAgentCommsError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            EmfAgentCommsError::EmfRabbitError(ref err) => Some(err),
            EmfAgentCommsError::SerdeJsonError(ref err) => Some(err),
            EmfAgentCommsError::OneshotCanceled(ref err) => Some(err),
        }
    }
}

impl From<EmfRabbitError> for EmfAgentCommsError {
    fn from(err: EmfRabbitError) -> Self {
        EmfAgentCommsError::EmfRabbitError(err)
    }
}

impl From<serde_json::error::Error> for EmfAgentCommsError {
    fn from(err: serde_json::error::Error) -> Self {
        EmfAgentCommsError::SerdeJsonError(err)
    }
}

impl From<oneshot::Canceled> for EmfAgentCommsError {
    fn from(err: oneshot::Canceled) -> Self {
        EmfAgentCommsError::OneshotCanceled(err)
    }
}
