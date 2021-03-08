// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql, command_utils::render_command_plan, display_utils::wrap_fut,
    error::EmfManagerCliError,
};
use emf_graphql_queries::state_machine as state_machine_queries;
use emf_wire_types::CommandPlan;
use std::{convert::TryInto, path::PathBuf};
use tokio::fs;

pub async fn cli(path: PathBuf) -> Result<(), EmfManagerCliError> {
    if !emf_fs::file_exists(&path).await {
        return Err(EmfManagerCliError::DoesNotExist(format!(
            "Input document at {} does not exist.",
            path.to_string_lossy()
        )));
    }

    let file = fs::read_to_string(&path).await?;

    let query = state_machine_queries::input_document::build(file);

    let resp: emf_graphql_queries::Response<state_machine_queries::input_document::Resp> =
        wrap_fut("Submitting Input...", graphql(query)).await?;

    let x = Result::from(resp)?.data.state_machine.submit_input_document;

    tracing::debug!(?x);

    let plan: CommandPlan = x.plan.try_into()?;

    render_command_plan(&plan)?;

    Ok(())
}
