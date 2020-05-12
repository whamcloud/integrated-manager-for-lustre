// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![recursion_limit = "256"]

#[cfg(feature = "postgres-interop")]
#[macro_use]
extern crate diesel;

pub mod models;
#[cfg(feature = "postgres-interop")]
pub mod schema;

#[cfg(feature = "postgres-interop")]
pub mod alerts;

#[cfg(feature = "postgres-interop")]
pub mod command;

#[cfg(feature = "postgres-interop")]
pub mod fidtaskqueue;

#[cfg(feature = "postgres-interop")]
pub mod hosts;

#[cfg(feature = "postgres-interop")]
pub mod job;

#[cfg(feature = "postgres-interop")]
pub mod lustrefid;

#[cfg(feature = "postgres-interop")]
pub mod profile;

#[cfg(feature = "postgres-interop")]
pub mod repo;

#[cfg(feature = "postgres-interop")]
pub mod step;

#[cfg(feature = "postgres-interop")]
pub mod task;

#[cfg(feature = "postgres-interop")]
use diesel::{
    prelude::RunQueryDsl,
    query_builder::{QueryFragment, QueryId},
    r2d2::{ConnectionManager, Pool},
    PgConnection,
};
#[cfg(feature = "postgres-interop")]
use iml_manager_env::get_db_conn_string;

#[cfg(feature = "postgres-interop")]
/// Allows for a generic return type for Insert statements, that can be used in either a sync or async
/// context.
pub trait Executable:
    RunQueryDsl<diesel::PgConnection> + QueryFragment<diesel::pg::Pg> + QueryId
{
}

#[cfg(feature = "postgres-interop")]
impl<T> Executable for T where
    T: RunQueryDsl<diesel::PgConnection> + QueryFragment<diesel::pg::Pg> + QueryId
{
}

#[cfg(feature = "postgres-interop")]
pub type DbPool = Pool<ConnectionManager<diesel::PgConnection>>;

#[cfg(feature = "postgres-interop")]
pub use tokio_diesel;

#[cfg(feature = "postgres-interop")]
pub use r2d2;

#[cfg(feature = "postgres-interop")]
/// Get a new connection pool based on the envs connection string.
pub fn pool() -> Result<DbPool, r2d2::Error> {
    let manager = ConnectionManager::<PgConnection>::new(get_db_conn_string());

    Pool::builder().build(manager)
}
