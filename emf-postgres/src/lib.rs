// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod alert;

use emf_manager_env::get_db_conn_string;
use emf_wire_types::Fqdn;
use futures::{
    lock::Mutex,
    task::{Context, Poll},
    Stream,
};
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
    let mut opts = PgConnectOptions::default().username(&emf_manager_env::get_db_user());

    opts = if let Some(x) = emf_manager_env::get_db_host() {
        opts.host(&x)
    } else {
        opts
    };

    opts = if let Some(x) = emf_manager_env::get_db_port() {
        opts.port(x)
    } else {
        opts
    };

    opts = if let Some(x) = emf_manager_env::get_db_name() {
        opts.database(&x)
    } else {
        opts
    };

    opts = if let Some(x) = emf_manager_env::get_db_password() {
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

/// Connect to the postgres instance running on the EMF manager
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

pub async fn fqdn_by_host_id(pool: &PgPool, id: i32) -> Result<String, sqlx::Error> {
    let fqdn = sqlx::query!(
        r#"SELECT fqdn FROM chroma_core_managedhost WHERE id=$1 and not_deleted = 't'"#,
        id
    )
    .fetch_one(pool)
    .await?
    .fqdn;

    Ok(fqdn)
}

pub async fn host_id_by_fqdn(fqdn: &Fqdn, pool: &PgPool) -> Result<Option<i32>, sqlx::Error> {
    let id = sqlx::query!(
        "select id from chroma_core_managedhost where fqdn = $1 and not_deleted = 't'",
        fqdn.to_string()
    )
    .fetch_optional(pool)
    .await?
    .map(|x| x.id);

    Ok(id)
}

pub async fn active_mgs_host_fqdn(
    fsname: &str,
    pool: &PgPool,
) -> Result<Option<String>, sqlx::Error> {
    let fsnames = &[fsname.into()][..];
    let maybe_active_mgs_host_id = sqlx::query!(
        r#"
            SELECT active_host_id from target WHERE filesystems @> $1 and name='MGS'
        "#,
        fsnames
    )
    .fetch_optional(pool)
    .await?
    .and_then(|x| x.active_host_id);

    tracing::trace!("Maybe active MGS host id: {:?}", maybe_active_mgs_host_id);

    if let Some(active_mgs_host_id) = maybe_active_mgs_host_id {
        let active_mgs_host_fqdn = fqdn_by_host_id(pool, active_mgs_host_id).await?;

        Ok(Some(active_mgs_host_fqdn))
    } else {
        Ok(None)
    }
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
