// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::graphql::Context;
use emf_wire_types::{json::GraphQLJson, Command, State};
use juniper::{FieldError, Value};

pub(crate) struct StateMachineQuery;

#[juniper::graphql_object(Context = Context)]
impl StateMachineQuery {
    /// Get a `Command` by id
    #[graphql(arguments(id(description = "The id of the `Command` to fetch"),))]
    async fn get_cmd(context: &Context, id: i32) -> juniper::FieldResult<Option<Command>> {
        let cmd = sqlx::query!(
            r#"
            SELECT id, plan, state as "state: State"
            FROM command_plan WHERE id = $1
            "#,
            id
        )
        .fetch_optional(&context.pg_pool)
        .await?
        .map(|cmd| Command {
            id: cmd.id,
            plan: GraphQLJson(cmd.plan),
            state: cmd.state,
        });

        Ok(cmd)
    }
}

pub(crate) struct StateMachineMutation;

#[juniper::graphql_object(Context = Context)]
impl StateMachineMutation {
    /// Submit an input document that will be passed into the state machine input handler, where it will be processed.
    #[graphql(arguments(document(
        description = "The input document being submitted in yaml format."
    ),))]
    async fn submit_input_document(
        context: &Context,
        document: String,
    ) -> juniper::FieldResult<Command> {
        let port = emf_manager_env::get_port("API_SERVICE_STATE_MACHINE_SERVICE_PORT");

        let resp = context
            .http_client
            .post(&format!("http://localhost:{}/submit", port))
            .body(document)
            .send()
            .await?;

        let status = resp.status();

        if status.is_client_error() || status.is_server_error() {
            let err_text = resp.text().await?;

            Err(FieldError::new(err_text, Value::null()))
        } else {
            Ok(resp.json().await?)
        }
    }
}
