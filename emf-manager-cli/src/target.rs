// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{get_hosts, graphql},
    display_utils::{wrap_fut, DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use console::Term;
use emf_graphql_queries::target as target_queries;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum TargetCommand {
    /// List known targets
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
        /// Optionally filter by filesystem name
        fsname: Option<String>,
    },
}

pub async fn target_cli(command: TargetCommand) -> Result<(), EmfManagerCliError> {
    match command {
        TargetCommand::List {
            display_type,
            fsname,
        } => {
            let hosts = get_hosts().await?;

            let query = target_queries::list::build(None, None, None, fsname, None);
            let resp: emf_graphql_queries::Response<target_queries::list::Resp> =
                wrap_fut("Fetching targets...", graphql(query)).await?;

            let targets = Result::from(resp)?.data.targets;
            let x = (hosts, targets).into_display_type(display_type);

            let term = Term::stdout();
            term.write_line(&x).unwrap();

            Ok(())
        }
    }
}
