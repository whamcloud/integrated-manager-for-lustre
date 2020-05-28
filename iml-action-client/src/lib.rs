// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    channel::oneshot,
    future::{self, Either},
    Future,
    FutureExt,
    TryFutureExt,
};
use iml_action_runner::ActionType;
use iml_manager_env::get_action_runner_connect;
use iml_wire_types::{Action, ActionId, ActionName, Fqdn};
use thiserror::Error;
use uuid::Uuid;

#[derive(Error, Debug)]
pub enum ImlActionClientError {
    #[error(transparent)]
    ReqwestError(#[from] reqwest::Error),
    #[error("Request Cancelled")]
    CancelledRequest,
}

pub fn invoke_rust_agent(
    host: impl Into<Fqdn> + Clone,
    command: impl Into<ActionName>,
    args: impl serde::Serialize,
) -> (oneshot::Sender<()>, impl Future<Output = Result<serde_json::Value, ImlActionClientError>>) {
    let request_id = Uuid::new_v4().to_hyphenated().to_string();
    let conn = get_action_runner_connect();

    let action = ActionType::Remote((
        host.clone().into(),
        Action::ActionStart {
            action: command.into(),
            args: serde_json::json!(args),
            id: ActionId(request_id.clone()),
        },
    ));

    let client = reqwest::Client::new();

    let (p, c) = oneshot::channel::<()>();

    let post = client
        .post(&conn)
        .json(&action)
        .send()
        .err_into()
        .and_then(|resp| resp.json().err_into())
        .boxed();

    let fut = async move {
        let either = future::select(c, post).await;

        match either {
            Either::Left((x, f)) => {
                if let Err(_) = x {
                    return f.await;
                };
                let cancel = ActionType::Remote((
                    host.into(),
                    Action::ActionCancel {
                        id: ActionId(request_id),
                    },
                ));
                let _rc = client.post(&conn).json(&cancel).send().await;
                Err(ImlActionClientError::CancelledRequest)
            }
            Either::Right((x, _)) => x,
        }
    };

    (p, fut)
}
