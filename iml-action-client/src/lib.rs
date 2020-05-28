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
use iml_manager_env::{get_action_runner_connect, get_action_runner_socket};
use iml_wire_types::{Action, ActionId, ActionName, Fqdn};
use lazy_static::lazy_static;
use std::io::BufRead;
use thiserror::Error;
use uuid::Uuid;

lazy_static! {
    static ref RUNNING_IN_DOCKER: bool = {
        match std::fs::File::open("/proc/self/cgroup") {
            Err(_) => false,
            Ok(file) => {
                let reader = std::io::BufReader::new(file);
                reader
                    .lines()
                    .filter(|l| {
                        l.as_ref().unwrap_or(&"".to_string()).split(':').nth(1) == Some("docker")
                    })
                    .next()
                    .is_some()
            }
        }
    };
}

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
    let conn = if *RUNNING_IN_DOCKER {
        get_action_runner_connect()
    } else {
        get_action_runner_socket()
    };
    let conn2 = conn.clone();

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

    let post = async move {
        client
            .post(&conn)
            .json(&action)
            .send()
            .await?
            .json()
            .err_into()
            .await
    }.boxed();

    let fut = future::select(c, post)
        .then(|either| async move {
            if let Either::Right((_,_)) = either {
                let cancel = ActionType::Remote((
                    host.into(),
                    Action::ActionCancel {
                        id: ActionId(request_id),
                    }
                ));
                let client = reqwest::Client::new();
                let _rc = client
                    .post(&conn2)
                    .json(&cancel)
                    .send()
                    .await;
            }
            either
        }).map(|either| match either {
            Either::Left((_, b)) => { drop(b); Err(ImlActionClientError::CancelledRequest) }
            Either::Right((a, _)) => a,
        });

    (p, fut)
}
