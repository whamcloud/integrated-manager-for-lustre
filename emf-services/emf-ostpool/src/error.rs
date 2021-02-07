// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Not Found")]
    NotFound,
    #[error(transparent)]
    SqlxError(#[from] emf_postgres::sqlx::Error),
}
