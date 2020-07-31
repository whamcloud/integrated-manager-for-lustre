// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::buf::BufExt as _;
use futures::{
    channel::oneshot,
    future::{self, Either},
    Future, FutureExt, TryFutureExt,
};
use hyper::{client::HttpConnector, Body, Client, Request};
use hyperlocal::{UnixClientExt as _, UnixConnector};
use iml_action_runner::ActionType;
use iml_manager_env::{get_action_runner_http, get_action_runner_uds, running_in_docker};
use iml_wire_types::{Action, ActionId, ActionName, Fqdn};
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
enum ClientWrapper {
    Http(Client<HttpConnector>),
    Unix(Client<UnixConnector>),
}

impl ClientWrapper {
    fn request(&self, req: Request<Body>) -> hyper::client::ResponseFuture {
        match self {
            ClientWrapper::Http(c) => c.request(req),
            ClientWrapper::Unix(c) => c.request(req),
        }
    }
}

fn client() -> ClientWrapper {
    if running_in_docker() {
        ClientWrapper::Http(Client::new())
    } else {
        ClientWrapper::Unix(Client::unix())
    }
}

// Return URI or painc
fn connect_uri() -> hyper::Uri {
    if running_in_docker() {
        get_action_runner_http().parse::<hyper::Uri>().unwrap()
    } else {
        hyperlocal::Uri::new(get_action_runner_uds(), "/").into()
    }
}

async fn build_invoke_rust_agent(
    host: impl Into<Fqdn> + Clone + Send,
    command: impl Into<ActionName> + Send,
    args: impl serde::Serialize + Send,
    client: ClientWrapper,
    request_id: String,
) -> Result<serde_json::Value, ImlActionClientError> {
    let uri = connect_uri();

    let action = ActionType::Remote((
        host.clone().into(),
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
        .uri(&uri)
        .body(Body::from({
            let s = serde_json::to_string(&action)?;
            tracing::debug!("REQUEST to {} BODY: {}", &uri, &s);
            s
        }))?;

    client
        .request(req)
        .err_into()
        .and_then(|resp| hyper::body::aggregate(resp).err_into())
        .map(|xs| match xs {
            Ok(body) => {
                let s = serde_json::from_reader(body.reader())
                    .map_err(ImlActionClientError::SerdeJsonError);
                tracing::debug!("RESULT from {} BODY: {:?}", &uri, &s);
                s
            }
            Err(e) => {
                tracing::debug!("RESULT from {} ERROR: {}", &uri, &e);
                Err(e)
            }
        })
        .await
}

pub async fn invoke_rust_agent(
    host: impl Into<Fqdn> + Clone + Send,
    command: impl Into<ActionName> + Send,
    args: impl serde::Serialize + Send,
) -> Result<serde_json::Value, ImlActionClientError> {
    let client = client();
    let request_id = Uuid::new_v4().to_hyphenated().to_string();

    build_invoke_rust_agent(host, command, args, client, request_id).await
}

// @@ This may want to use futures::future::Abortable instead
pub fn invoke_rust_agent_cancelable(
    host: impl Into<Fqdn> + Clone + Send,
    command: impl Into<ActionName> + Send,
    args: impl serde::Serialize + Send,
) -> Result<
    (
        oneshot::Sender<()>,
        impl Future<Output = Result<serde_json::Value, ImlActionClientError>>,
    ),
    ImlActionClientError,
> {
    let client = client();
    let request_id = Uuid::new_v4().to_hyphenated().to_string();

    let host2 = host.clone();
    let client2 = client.clone();
    let request_id2 = request_id.clone();

    let post = build_invoke_rust_agent(host, command, args, client, request_id);

    let (p, c) = oneshot::channel::<()>();

    let fut = async move {
        let either = future::select(c, post.boxed()).await;

        match either {
            Either::Left((x, f)) => {
                if x.is_err() {
                    return f.await;
                }
                let cancel = ActionType::Remote((
                    host2.into(),
                    Action::ActionCancel {
                        id: ActionId(request_id2),
                    },
                ));
                let uri = connect_uri()?;
                let req = Request::builder()
                    .method("POST")
                    .uri(&uri)
                    .body(Body::from(serde_json::to_string(&cancel)?));

                if let Ok(req) = req {
                    let _rc = client2.request(req).await;
                }
                Err(ImlActionClientError::CancelledRequest)
            }
            Either::Right((x, _)) => x,
        }
    };

    Ok((p, fut))
}
