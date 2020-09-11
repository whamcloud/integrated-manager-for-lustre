// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod snapshot;

/// The base query that is serialized and sent
/// to the graphql server
#[derive(serde::Serialize)]
pub struct Query<T: serde::Serialize> {
    query: String,
    variables: Option<T>,
}
