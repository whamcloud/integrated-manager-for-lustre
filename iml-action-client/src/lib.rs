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
    #[error("Request Cancelled")]
    CancelledRequest,
    #[error("HTTP Error {0}")]
    HttpError(String),
    #[error(transparent)]
    SerdeJsonError(serde_json::error::Error),
}

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

fn connect_uri() -> hyper::Uri {
    if running_in_docker() {
        get_action_runner_http().parse::<hyper::Uri>().unwrap()
    } else {
        hyperlocal::Uri::new(get_action_runner_uds(), "/").into()
    }
}

fn connect_uri() -> hyper::Uri {
    if running_in_docker() {
        get_action_runner_http().parse::<hyper::Uri>().unwrap()
    } else {
        hyperlocal::Uri::new(get_action_runner_uds(), "/").into()
    }
}

pub fn invoke_rust_agent(
    host: impl Into<Fqdn> + Clone,
    command: impl Into<ActionName>,
    args: impl serde::Serialize,
) -> (
    oneshot::Sender<()>,
    impl Future<Output = Result<serde_json::Value, ImlActionClientError>>,
) {
    let request_id = Uuid::new_v4().to_hyphenated().to_string();
    let uri = connect_uri();

    let action = ActionType::Remote((
        host.clone().into(),
        Action::ActionStart {
            action: command.into(),
            args: serde_json::json!(args),
            id: ActionId(request_id.clone()),
        },
    ));

    let client = client();

    let (p, c) = oneshot::channel::<()>();

    let req = Request::builder()
        .method(hyper::Method::POST)
        .header(hyper::header::ACCEPT, "application/json")
        .header(hyper::header::CONTENT_TYPE, "application/json")
        .uri(&uri)
        .body(Body::from(serde_json::to_string(&action).unwrap()))
        .unwrap();

    let post = client
        .request(req)
        .err_into()
        .and_then(|resp| hyper::body::aggregate(resp).err_into())
        .map_ok(|body| {
            serde_json::from_reader(body.reader()).unwrap_or(serde_json::from_str("[]").unwrap())
        })
        .boxed();

    let fut = async move {
        let either = future::select(c, post).await;

        match either {
            Either::Left((x, f)) => {
                if x.is_err() {
                    return f.await;
                }
                let cancel = ActionType::Remote((
                    host.into(),
                    Action::ActionCancel {
                        id: ActionId(request_id),
                    },
                ));
                let req = Request::builder()
                    .method("POST")
                    .uri(&uri)
                    .body(Body::from(serde_json::to_string(&cancel).unwrap()))
                    .unwrap();

                let _rc = client.request(req).await;
                Err(ImlActionClientError::CancelledRequest)
            }
            Either::Right((x, _)) => x,
        }
    };

    (p, fut)
}
