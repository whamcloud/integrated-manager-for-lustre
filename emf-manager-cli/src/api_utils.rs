// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{display_utils::wrap_fut, error::EmfManagerCliError};
use emf_graphql_queries::{filesystem as filesystem_queries, host as host_queries};
use emf_wire_types::{Filesystem, Host};
use std::fmt::Debug;

#[derive(serde::Serialize)]
pub struct SendJob<T> {
    pub class_name: String,
    pub args: T,
}

#[derive(serde::Serialize)]
pub struct SendCmd<T> {
    pub jobs: Vec<SendJob<T>>,
    pub message: String,
}

pub async fn graphql<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    query: impl serde::Serialize + Debug,
) -> Result<T, EmfManagerCliError> {
    let client = emf_manager_client::get_client()?;

    emf_manager_client::graphql(client, query)
        .await
        .map_err(|e| e.into())
}

pub async fn get_influx<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    db: &str,
    influxql: &str,
) -> Result<T, EmfManagerCliError> {
    let client = emf_manager_client::get_client()?;

    emf_manager_client::get_influx(client, db, influxql)
        .await
        .map_err(|e| e.into())
}

pub async fn get_hosts() -> Result<Vec<Host>, EmfManagerCliError> {
    let query = host_queries::list::build();
    let resp: emf_graphql_queries::Response<host_queries::list::Resp> =
        wrap_fut("Fetching hosts...", graphql(query)).await?;

    let xs = Result::from(resp)?.data.host.list;

    Ok(xs)
}

pub async fn get_filesystem(name: &str) -> Result<Filesystem, EmfManagerCliError> {
    let query = filesystem_queries::by_name::build(name);
    let resp: emf_graphql_queries::Response<filesystem_queries::by_name::Resp> =
        wrap_fut("Fetching Filesystem...", graphql(query)).await?;

    Result::from(resp)?
        .data
        .filesystem
        .by_name
        .ok_or_else(|| EmfManagerCliError::DoesNotExist(format!("Filesystem {}", &name)))
}

pub async fn get_filesystems() -> Result<Vec<Filesystem>, EmfManagerCliError> {
    let query = filesystem_queries::list::build();
    let resp: emf_graphql_queries::Response<filesystem_queries::list::Resp> =
        wrap_fut("Fetching Filesystem...", graphql(query)).await?;

    let xs = Result::from(resp)?.data.filesystem.list;

    Ok(xs)
}
