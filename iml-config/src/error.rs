// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum ImlConfigError {
    #[error("IO Error")]
    IoError(#[from] std::io::Error),
    #[error("Couldn't convert bytes to string")]
    FromUtf8Error(#[from] std::string::FromUtf8Error),
}