// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::EmfAgentError, rpm};

pub use rpm::Version;

pub async fn installed(package: String) -> Result<bool, EmfAgentError> {
    rpm::installed(&package).await
}

pub async fn version(package: String) -> Result<Option<Version>, EmfAgentError> {
    rpm::version(&package).await
}
