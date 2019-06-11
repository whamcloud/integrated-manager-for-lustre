// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone)]
pub enum ActionDropdownError {
    Cancelled(futures::sync::oneshot::Canceled),
    FailedFetch(seed::fetch::FailReason),
}

impl std::fmt::Display for ActionDropdownError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ActionDropdownError::Cancelled(ref err) => write!(f, "{}", err),
            ActionDropdownError::FailedFetch(ref err) => write!(f, "{:?}", err),
        }
    }
}

impl std::error::Error for ActionDropdownError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ActionDropdownError::Cancelled(ref err) => Some(err),
            ActionDropdownError::FailedFetch(_) => None,
        }
    }
}

impl From<futures::sync::oneshot::Canceled> for ActionDropdownError {
    fn from(err: futures::sync::oneshot::Canceled) -> Self {
        ActionDropdownError::Cancelled(err)
    }
}

impl From<seed::fetch::FailReason> for ActionDropdownError {
    fn from(err: seed::fetch::FailReason) -> Self {
        ActionDropdownError::FailedFetch(err)
    }
}
