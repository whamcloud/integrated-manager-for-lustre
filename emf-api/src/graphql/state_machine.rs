// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::graphql::Context;
use emf_wire_types::Command;

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

        let x = resp.bytes().await?;

        Ok(Command { id: 1 })
    }
}
