// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql,
    display_utils::{wrap_fut, DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use console::Term;
use emf_graphql_queries::alert as alert_queries;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum Command {
    /// List alerts (default)
    #[structopt(name = "list")]
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
        /// Only show active / inactive alerts
        #[structopt(short, long)]
        active: Option<bool>,
    },
}

async fn list(display_type: DisplayType, active: Option<bool>) -> Result<(), EmfManagerCliError> {
    let mut builder = alert_queries::list::Builder::new();

    if let Some(x) = active {
        builder = builder.with_active(x);
    }

    let query = builder.build();

    let resp: emf_graphql_queries::Response<alert_queries::list::Resp> =
        wrap_fut("Fetching alerts...", graphql(query)).await?;

    let xs = Result::from(resp)?.data.alert.list.data;

    let term = Term::stdout();

    tracing::debug!(?xs);

    let x = xs.into_display_type(display_type);

    term.write_line(&x).unwrap();

    Ok(())
}

pub async fn cli(command: Option<Command>) -> Result<(), EmfManagerCliError> {
    alert(command.unwrap_or(Command::List {
        display_type: DisplayType::Tabular,
        active: Some(true),
    }))
    .await
}

async fn alert(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::List {
            display_type,
            active,
        } => list(display_type, active).await?,
    };

    Ok(())
}
