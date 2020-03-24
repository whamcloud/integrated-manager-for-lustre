// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, rpm};

pub use rpm::Version;

pub async fn installed(package: String) -> Result<bool, ImlAgentError> {
    rpm::installed(&package).await
}

pub async fn version(package: String) -> Result<Option<Version>, ImlAgentError> {
    rpm::version(&package).await
}
