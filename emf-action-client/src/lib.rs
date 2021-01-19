// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::buf::BufExt as _;
use emf_manager_env::{get_action_runner_http, get_action_runner_uds, running_in_docker};
use emf_wire_types::{Action, ActionId, ActionName, ActionType, AgentResult, Fqdn};
use hyper::{client::HttpConnector, Body, Request};
use hyperlocal::{UnixClientExt as _, UnixConnector};
use std::{ops::Deref, sync::Arc};
use thiserror::Error;
use uuid::Uuid;

#[derive(Error, Debug)]
pub enum EmfActionClientError {
    #[error(transparent)]
    HyperError(#[from] hyper::Error),
    #[error(transparent)]
    UriError(hyper::http::uri::InvalidUri),
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
    pub async fn invoke_rust_agent(
        &self,
        host: impl Into<Fqdn>,
        action: impl Into<ActionName> + Send,
        args: impl serde::Serialize + Send,
        uuid: impl Into<Option<&Uuid>>,
    ) -> Result<serde_json::Value, EmfActionClientError> {
        let id = match uuid.into() {
            Some(x) => x.to_hyphenated().to_string(),
            None => Uuid::new_v4().to_hyphenated().to_string(),
        };

        let action = Action::ActionStart {
            action: action.into(),
            args: serde_json::json!(args),
            id: ActionId(id),
        };

        build_invoke_rust_agent(Arc::clone(&self.inner), Arc::clone(&self.uri), host, action).await
    }
    pub async fn invoke_rust_agent_expect_result(
        &self,
        host: impl Into<Fqdn>,
        action: impl Into<ActionName> + Send,
        args: impl serde::Serialize + Send,
        uuid: impl Into<Option<&Uuid>>,
    ) -> Result<AgentResult, EmfActionClientError> {
        let x = self.invoke_rust_agent(host, action, args, uuid).await?;
        let x = serde_json::from_value(x)?;

        Ok(x)
    }
    pub async fn cancel_request(
        &self,
        host: impl Into<Fqdn> + Clone,
        uuid: &Uuid,
    ) -> Result<(), EmfActionClientError> {
        let action = Action::ActionCancel {
            id: ActionId(uuid.to_hyphenated().to_string()),
        };

        let x =
            build_invoke_rust_agent(Arc::clone(&self.inner), Arc::clone(&self.uri), host, action)
                .await?;

        tracing::info!("Cancelled request: {}. Resp: {:?}", uuid, x);

        Ok(())
    }
}

async fn build_invoke_rust_agent(
    client: Arc<ClientInner>,
    uri: Arc<hyper::Uri>,
    host: impl Into<Fqdn>,
    action: Action,
) -> Result<serde_json::Value, EmfActionClientError> {
    let action = ActionType::Remote((host.into(), action));

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
