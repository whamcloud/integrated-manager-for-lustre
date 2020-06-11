// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    lock::Mutex,
    task::{Context, Poll},
    Stream,
};
use iml_manager_env::get_db_conn_string;
use std::{pin::Pin, sync::Arc};
pub use tokio_postgres::{
    error::DbError,
    row::Row,
    types::{self, FromSql, IsNull, ToSql, Type},
    AsyncMessage, Client, Error, Transaction,
};
use tokio_postgres::{tls::NoTlsStream, Connection, NoTls, Socket};

#[cfg(feature = "pool")]
pub mod pool;

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
