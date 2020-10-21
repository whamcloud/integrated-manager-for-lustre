// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::buf::BufExt as _;
use futures::{
    future::{abortable, AbortHandle, Aborted},
    Future,
};
use hyper::{client::HttpConnector, Body, Request};
use hyperlocal::{UnixClientExt as _, UnixConnector};
use iml_manager_env::{get_action_runner_http, get_action_runner_uds, running_in_docker};
use iml_wire_types::{Action, ActionId, ActionName, ActionType, Fqdn};
use std::{ops::Deref, sync::Arc};
use thiserror::Error;
use uuid::Uuid;

#[derive(Error, Debug)]
pub enum ImlActionClientError {
    #[error(transparent)]
    HyperError(#[from] hyper::Error),
    #[error(transparent)]
    UriError(hyper::http::uri::InvalidUri),
    #[error("Request Cancelled")]
    CancelledRequest,
    #[error(transparent)]
    HttpError(#[from] hyper::http::Error),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::error::Error),
}

#[derive(Clone)]
enum ClientInner {
    Http(hyper::Client<HttpConnector>),
    Unix(hyper::Client<UnixConnector>),
}

impl ClientInner {
    fn request(&self, req: Request<Body>) -> hyper::client::ResponseFuture {
        match self {
            ClientInner::Http(c) => c.request(req),
            ClientInner::Unix(c) => c.request(req),
        }
    }
}

/// This `Client` performs calls to the `action-runner` service.
///
/// Use it to invoke action plugins on storage servers.
#[derive(Clone)]
pub struct Client {
    inner: Arc<ClientInner>,
    uri: Arc<hyper::Uri>,
}

impl Default for Client {
    /// Create a new client instance
    ///
    /// # Panics
    ///
    /// Panics if internal action runner URI cannot be parsed to a `hyper::Uri`.
    fn default() -> Self {
        let (inner, uri) = if running_in_docker() {
            (
                ClientInner::Http(hyper::Client::new()),
                get_action_runner_http().parse::<hyper::Uri>().unwrap(),
            )
        } else {
            (
                ClientInner::Unix(hyper::Client::unix()),
                hyperlocal::Uri::new(get_action_runner_uds(), "/").into(),
            )
        };

        Client {
            inner: Arc::new(inner),
            uri: Arc::new(uri),
        }
    }
}

impl Client {
    /// Invoke the given action plugin on the given `host`
    ///
    /// *Note*: There is no way to cancel this fn, use `invoke_rust_agent_cancelable`
    /// If you need to cancel.
    pub async fn invoke_rust_agent(
        &self,
        host: impl Into<Fqdn>,
        command: impl Into<ActionName> + Send,
        args: impl serde::Serialize + Send,
    ) -> Result<serde_json::Value, ImlActionClientError> {
        let request_id = Uuid::new_v4().to_hyphenated().to_string();

        build_invoke_rust_agent(
            Arc::clone(&self.inner),
            Arc::clone(&self.uri),
            host,
            command,
            args,
            request_id,
        )
        .await
    }
    /// Invoke the given action plugin on the given `host`.
    ///
    /// Returns an `AbortHandle`. When aborted, the
    /// action plugin is cancelled.
    pub fn invoke_rust_agent_cancelable(
        &self,
        host: impl Into<Fqdn> + Clone,
        command: impl Into<ActionName>,
        args: impl serde::Serialize,
    ) -> Result<
        (
            AbortHandle,
            impl Future<Output = Result<serde_json::Value, ImlActionClientError>>,
        ),
        ImlActionClientError,
    > {
        let request_id = Uuid::new_v4().to_hyphenated().to_string();

        let host2 = host.clone();
        let request_id2 = request_id.clone();

        let inner = Arc::clone(&self.inner);

        let uri = Arc::clone(&self.uri);

        let post = build_invoke_rust_agent(
            Arc::clone(&self.inner),
            Arc::clone(&self.uri),
            host,
            command,
            args,
            request_id,
        );

        let (fut, handle) = abortable(post);

        let fut = async move {
            let x = fut.await;

            match x {
                Ok(x) => x,
                Err(Aborted) => {
                    let cancel = ActionType::Remote((
                        host2.into(),
                        Action::ActionCancel {
                            id: ActionId(request_id2),
                        },
                    ));

                    let req = Request::builder()
                        .method("POST")
                        .uri(uri.deref())
                        .body(Body::from(serde_json::to_string(&cancel)?));

                    if let Ok(req) = req {
                        let _rc = inner.request(req).await;
                    }

                    Err(ImlActionClientError::CancelledRequest)
                }
            }
        };

        Ok((handle, fut))
    }
}

async fn build_invoke_rust_agent(
    client: Arc<ClientInner>,
    uri: Arc<hyper::Uri>,
    host: impl Into<Fqdn>,
    command: impl Into<ActionName>,
    args: impl serde::Serialize,
    request_id: String,
) -> Result<serde_json::Value, ImlActionClientError> {
    let action = ActionType::Remote((
        host.into(),
        Action::ActionStart {
            action: command.into(),
            args: serde_json::json!(args),
            id: ActionId(request_id.clone()),
        },
    ));

    let req = Request::builder()
        .method(hyper::Method::POST)
        .header(hyper::header::ACCEPT, "application/json")
        .header(hyper::header::CONTENT_TYPE, "application/json")
        .uri(uri.deref())
        .body(Body::from({
            let s = serde_json::to_string(&action)?;

            tracing::debug!("REQUEST to {} BODY: {}", &uri, &s);

            s
        }))?;

    let resp = client.request(req).await?;

    let buf = hyper::body::aggregate(resp).await?;

    let x = serde_json::from_reader(buf.reader())?;

    tracing::debug!("RESULT from {} BODY: {:?}", uri, x);

    Ok(x)
}
