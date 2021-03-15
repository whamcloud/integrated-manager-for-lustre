// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql,
    command_utils::{render_command_details, render_command_plan},
    display_utils::{wrap_fut, DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use emf_graphql_queries::state_machine as state_machine_queries;
use emf_wire_types::CommandPlan;
use std::convert::TryInto;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum Command {
    /// List all commands (default)
    #[structopt(name = "list")]
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Display summary of a command
    #[structopt(name = "show")]
    Show {
        /// The command id
        id: i32,
    },
    /// Display details of a command, including status start, end times, and stdout / stderr of all actions
    #[structopt(name = "detail")]
    Detail {
        /// The command id
        id: i32,
    },
}

pub async fn cli(cmd: Option<Command>) -> Result<(), EmfManagerCliError> {
    let cmd = cmd.unwrap_or_else(|| Command::List {
        display_type: DisplayType::Tabular,
    });

    match cmd {
        Command::List { display_type } => {
            let query = state_machine_queries::list_cmds::build();

            let resp: emf_graphql_queries::Response<state_machine_queries::list_cmds::Resp> =
                wrap_fut("Fetching cmds...", graphql(query)).await?;

            let xs = Result::from(resp)?.data.state_machine.list_cmds;

            tracing::debug!(?xs);

            if xs.is_empty() {
                return Err(EmfManagerCliError::ConfigError(format!(
                    "No commands found"
                )));
            }

            let x = xs.into_display_type(display_type);

            println!("{}", x);
        }
        Command::Show { id } => {
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
        }
        Command::Detail { id } => {
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

            render_command_details(&plan)?;
        }
    };

    Ok(())
}
