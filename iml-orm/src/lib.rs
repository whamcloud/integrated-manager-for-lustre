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
use diesel::{
    r2d2::{ConnectionManager, Pool},
    PgConnection,
};
#[cfg(feature = "postgres-interop")]
use iml_manager_env::get_db_conn_string;

#[cfg(feature = "postgres-interop")]
/// Get a new connection pool based on the envs connection string.
pub fn pool() -> Result<Pool<ConnectionManager<diesel::PgConnection>>, r2d2::Error> {
    let manager = ConnectionManager::<PgConnection>::new(get_db_conn_string());

    Pool::builder().build(manager)
}
