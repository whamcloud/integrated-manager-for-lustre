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

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Data<T> {
    pub data: T,
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Location {
    line: u32,
    column: u32,
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Error {
    message: String,
    locations: Vec<Location>,
    path: Vec<String>,
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Errors {
    errors: Vec<Error>,
}

#[derive(Debug, Clone, serde::Deserialize)]
#[serde(untagged)]
pub enum Response<T> {
    Data(Data<T>),
    Errors(Errors),
}
