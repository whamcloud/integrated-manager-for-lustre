// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql, command_utils::render_command_plan, display_utils::wrap_fut,
    error::EmfManagerCliError,
};
use emf_graphql_queries::state_machine as state_machine_queries;
use emf_wire_types::CommandPlan;
use std::convert::TryInto;

pub async fn cli(id: i32) -> Result<(), EmfManagerCliError> {
    let query = state_machine_queries::get_cmd::build(id);

    let resp: emf_graphql_queries::Response<state_machine_queries::get_cmd::Resp> =
        wrap_fut("Fetching cmd...", graphql(query)).await?;

    let x = Result::from(resp)?.data.state_machine.get_cmd;

    tracing::debug!(?x);

    let x = match x {
        Some(x) => x,
        None => {
            return Err(EmfManagerCliError::ConfigError(format!(
                "Command with id {} not found",
                id
            )))
        }
    };

    let plan: CommandPlan = x.plan.try_into()?;

    render_command_plan(&plan)?;

    Ok(())
}
