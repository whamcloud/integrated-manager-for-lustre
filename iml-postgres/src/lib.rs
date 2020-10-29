// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod alert;
pub mod db;

use futures::{
    lock::Mutex,
    task::{Context, Poll},
    Stream,
};
use iml_manager_env::get_db_conn_string;
use sqlx::postgres::{PgConnectOptions, PgPoolOptions};
pub use sqlx::{self, postgres::PgPool};
use std::{pin::Pin, sync::Arc};
pub use tokio_postgres::{
    error::DbError,
    row::Row,
    types::{self, FromSql, IsNull, ToSql, Type},
    AsyncMessage, Client, Error, Transaction,
};
use tokio_postgres::{tls::NoTlsStream, Connection, NoTls, Socket};

pub async fn get_db_pool(pool_size: u32) -> Result<PgPool, sqlx::Error> {
    let mut opts = PgConnectOptions::default().username(&iml_manager_env::get_db_user());

    opts = if let Some(x) = iml_manager_env::get_db_host() {
        opts.host(&x)
    } else {
        opts
    };

    opts = if let Some(x) = iml_manager_env::get_db_port() {
        opts.port(x)
    } else {
        opts
    };

    opts = if let Some(x) = iml_manager_env::get_db_name() {
        opts.database(&x)
    } else {
        opts
    };

    opts = if let Some(x) = iml_manager_env::get_db_password() {
        opts.password(&x)
    } else {
        opts
    };

    let x = PgPoolOptions::new()
        .max_connections(pool_size)
        .connect_with(opts)
        .await?;

    Ok(x)
}

/// Connect to the postgres instance running on the IML manager
///
/// This fn is useful for production code as it reads in env vars
/// to make a connection.
///
pub async fn connect() -> Result<(Client, Connection<Socket, NoTlsStream>), Error> {
    tokio_postgres::connect(&get_db_conn_string(), NoTls).await
}

pub type SharedClient = Arc<Mutex<Client>>;

/// Allows for the client to be shared across threads.
pub fn shared_client(client: Client) -> SharedClient {
    Arc::new(Mutex::new(client))
}

/// Wraps the `Connection` `poll_message` fn so it can be
/// used as a stream
pub struct NotifyStream(pub Connection<Socket, NoTlsStream>);

impl Stream for NotifyStream {
    type Item = Result<AsyncMessage, Error>;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context) -> Poll<Option<Self::Item>> {
        self.0.poll_message(cx)
    }
}

pub async fn select_all<'a, I>(
    client: &mut Client,
    query: &str,
    params: I,
) -> Result<impl Stream<Item = Result<Row, Error>>, Error>
where
    I: IntoIterator<Item = &'a dyn ToSql>,
    I::IntoIter: ExactSizeIterator,
{
    let s = client.prepare(&query).await?;

    client.query_raw(&s, params).await
}

#[cfg(feature = "test")]
use dotenv::dotenv;

/// Setup for a test run. This fn hands out a pool
/// with a single connection and starts a transaction for it.
/// The transaction is rolled back when the connection closes
/// so nothing is written to the database.
#[cfg(feature = "test")]
pub async fn test_setup() -> Result<PgPool, sqlx::Error> {
    dotenv().ok();

    let pool = get_db_pool(1).await?;

    sqlx::query("BEGIN TRANSACTION").execute(&pool).await?;

    Ok(pool)
}
