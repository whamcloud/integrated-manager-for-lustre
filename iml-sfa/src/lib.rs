// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod db;
mod sfa_class_ext;

use iml_postgres::sqlx;
use iml_wire_types::sfa::wbem_interop::SfaClassError;
pub use sfa_class_ext::SfaClassExt;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ImlSfaError {
    #[error(transparent)]
    WbemClient(#[from] wbem_client::WbemClientError),
    #[error(transparent)]
    SfaClassError(#[from] SfaClassError),
    #[error(transparent)]
    SqlxCoreError(#[from] sqlx::Error),
}
