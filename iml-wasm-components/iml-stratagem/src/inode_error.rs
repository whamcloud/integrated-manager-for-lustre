// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::inode_table::InfluxResults;

#[derive(Debug, Clone)]
pub enum InodeError {
    Cancelled(futures::sync::oneshot::Canceled),
    FailedFetch(seed::fetch::FailReason<InfluxResults>),
}

impl std::fmt::Display for InodeError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            InodeError::Cancelled(ref err) => write!(f, "{}", err),
            InodeError::FailedFetch(ref err) => write!(f, "{:?}", err),
        }
    }
}

impl std::error::Error for InodeError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            InodeError::Cancelled(ref err) => Some(err),
            InodeError::FailedFetch(_) => None,
        }
    }
}

impl From<futures::sync::oneshot::Canceled> for InodeError {
    fn from(err: futures::sync::oneshot::Canceled) -> Self {
        InodeError::Cancelled(err)
    }
}

impl From<seed::fetch::FailReason<InfluxResults>> for InodeError {
    fn from(err: seed::fetch::FailReason<InfluxResults>) -> Self {
        InodeError::FailedFetch(err)
    }
}
