// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use hyper::{
    client::{
        connect::{Connect, Connected, Destination},
        HttpConnector,
    },
    Client,
};
use native_tls::Identity;
use std::{io, sync::Arc};
use tokio::{net::TcpStream, prelude::*};
use tokio_tls::{TlsConnector, TlsStream};

/// Creates a HTTPS client that will send requests
pub fn build_https_client(pfx: &[u8]) -> Result<Client<HttpsConnector>, ImlAgentError> {
    let id = Identity::from_pkcs12(pfx, "")?;
    let tls_conn = TlsConnector::from(
        native_tls::TlsConnector::builder()
            .identity(id)
            .danger_accept_invalid_certs(true)
            .build()?,
    );
    let mut https_conn = HttpsConnector::new(tls_conn);

    https_conn.http.enforce_http(false);

    Ok(Client::builder().build(https_conn))
}

pub struct HttpsConnector {
    tls: Arc<TlsConnector>,
    pub http: HttpConnector,
}

impl HttpsConnector {
    pub fn new(x: TlsConnector) -> Self {
        HttpsConnector {
            tls: Arc::new(x),
            http: HttpConnector::new(2),
        }
    }
}

impl Connect for HttpsConnector {
    type Transport = TlsStream<TcpStream>;
    type Error = io::Error;
    type Future = Box<Future<Item = (Self::Transport, Connected), Error = Self::Error> + Send>;

    fn connect(&self, dst: Destination) -> Self::Future {
        if dst.scheme() != "https" {
            return Box::new(futures::future::err(io::Error::new(
                io::ErrorKind::Other,
                "only works with https",
            )));
        }

        let host = format!(
            "{}{}",
            dst.host(),
            dst.port()
                .map(|p| format!(":{}", p))
                .unwrap_or_else(|| "".into())
        );

        let tls_cx = self.tls.clone();
        Box::new(self.http.connect(dst).and_then(move |(tcp, connected)| {
            tls_cx
                .connect(&host, tcp)
                .map(|s| (s, connected))
                .map_err(|e| io::Error::new(io::ErrorKind::Other, e))
        }))
    }
}
