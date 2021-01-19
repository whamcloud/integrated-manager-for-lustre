// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

/// The order of Role is order of preference for returning in a cloned
/// pacemaker resource.
#[derive(Debug, PartialEq, PartialOrd, Eq, Ord)]
pub enum Role {
    Error(String),
    Started,
    Starting,
    Stopping,
    Stopped,
}

impl From<&str> for Role {
    fn from(role: &str) -> Self {
        match role {
            "Started" => Role::Started,
            "Starting" => Role::Starting,
            "Stopping" => Role::Stopping,
            "Stopped" => Role::Stopped,
            other => Role::Error(other.to_string()),
        }
    }
}
