// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future, StreamExt, TryStreamExt};
use iml_action_runner::ActionType;
use iml_fs::stream_file_lines;
use iml_manager_env::{get_action_runner_connect, get_action_runner_socket};
use iml_wire_types::{Action, ActionId, ActionName, AgentResult, Fqdn};
use uuid::Uuid;

async fn running_in_docker() -> bool {
    stream_file_lines("/proc/self/cgroup")
        .boxed()
        .try_filter(|l| future::ready(l.split(':').nth(1) == Some("docker")))
        .try_next()
        .await
        .unwrap_or(None)
        .is_some()
}

pub async fn invoke_rust_agent(
    host: impl Into<Fqdn>,
    command: impl Into<ActionName>,
    args: serde_json::Value,
) -> AgentResult {
    let request_id = Uuid::new_v4().to_hyphenated().to_string();
    let conn = if running_in_docker().await {
        get_action_runner_connect()
    } else {
        get_action_runner_socket()
    };

    let action = ActionType::Remote((
        host.into(),
        Action::ActionStart {
            action: command.into(),
            args,
            id: ActionId(request_id),
        },
    ));

    let client = reqwest::Client::new();

    client
        .post(&conn)
        .json(&action)
        .send()
        .await
        .map_err(|e| format!("Send Failed: {:?}", e))?
        .json()
        .await
        .map_err(|e| format!("Jsonify Failed: {:?}", e))
}
