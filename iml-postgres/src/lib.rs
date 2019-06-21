// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{Poll, Stream};
use iml_manager_env::{get_db_host, get_db_name, get_db_password, get_db_user};

use parking_lot::Mutex;
use std::sync::Arc;
pub use tokio_postgres::AsyncMessage;
use tokio_postgres::{tls::NoTlsStream, Client, Connection, NoTls, Socket};

/// Gets a connection string from the IML env
fn get_conn_string() -> String {
    let mut xs = vec![format!("user={}", get_db_user())];

    let host = match get_db_host() {
        Some(x) => x,
        None => "/var/run/postgresql".into(),
    };

    xs.push(format!("host={}", host));

    if let Some(x) = get_db_name() {
        xs.push(format!("dbname={}", x));
    }

    if let Some(x) = get_db_password() {
        xs.push(format!("password={}", x));
    }

    let s = xs.join(" ");

    log::debug!("conn: {}", s);

    s
}

/// Connect to the postgres instance running on the IML manager
///
/// This fn is useful for production code as it reads in env vars
/// to make a connection.
///
pub fn connect() -> tokio_postgres::impls::Connect<tokio_postgres::tls::NoTls> {
    tokio_postgres::connect(&get_conn_string(), NoTls)
}

/// Allows for the client to be shared across threads.
pub fn shared_client(client: Client) -> Arc<Mutex<Client>> {
    Arc::new(Mutex::new(client))
}

/// Wraps the `Connection` `poll_message` fn so it can be
/// used as a stream
pub struct NotifyStream(pub Connection<Socket, NoTlsStream>);

impl Stream for NotifyStream {
    type Item = AsyncMessage;
    type Error = tokio_postgres::Error;

    fn poll(&mut self) -> Poll<Option<Self::Item>, Self::Error> {
        self.0.poll_message()
    }
}
