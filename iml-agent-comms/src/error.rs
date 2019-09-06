// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::channel::oneshot;
use iml_rabbit::ImlRabbitError;

#[derive(Debug)]
pub enum ImlAgentCommsError {
    ImlRabbitError(ImlRabbitError),
    SerdeJsonError(serde_json::error::Error),
    OneshotCanceled(oneshot::Canceled),
}

impl std::fmt::Display for ImlAgentCommsError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlAgentCommsError::ImlRabbitError(ref err) => write!(f, "{}", err),
            ImlAgentCommsError::SerdeJsonError(ref err) => write!(f, "{}", err),
            ImlAgentCommsError::OneshotCanceled(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlAgentCommsError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlAgentCommsError::ImlRabbitError(ref err) => Some(err),
            ImlAgentCommsError::SerdeJsonError(ref err) => Some(err),
            ImlAgentCommsError::OneshotCanceled(ref err) => Some(err),
        }
    }
}

impl From<ImlRabbitError> for ImlAgentCommsError {
    fn from(err: ImlRabbitError) -> Self {
        ImlAgentCommsError::ImlRabbitError(err)
    }
}

impl From<serde_json::error::Error> for ImlAgentCommsError {
    fn from(err: serde_json::error::Error) -> Self {
        ImlAgentCommsError::SerdeJsonError(err)
    }
}

impl From<oneshot::Canceled> for ImlAgentCommsError {
    fn from(err: oneshot::Canceled) -> Self {
        ImlAgentCommsError::OneshotCanceled(err)
    }
}
