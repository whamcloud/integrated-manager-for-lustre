// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    cmd::{self},
};

/// Runs lctl with given arguments
pub async fn lctl(args: Vec<String>) -> Result<String, ImlAgentError> {
    cmd::lctl(args.iter().map(|s| s.as_ref()).collect())
        .await
        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
}
