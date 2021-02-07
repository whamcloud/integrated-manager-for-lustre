// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::get_hosts,
    display_utils::{DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use console::Term;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers (default)
    #[structopt(name = "list")]
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
}

async fn list_server(display_type: DisplayType) -> Result<(), EmfManagerCliError> {
    let hosts = get_hosts().await?;

    let term = Term::stdout();

    tracing::debug!(?hosts);

    let x = hosts.into_display_type(display_type);

    term.write_line(&x).unwrap();

    Ok(())
}

pub async fn server_cli(command: Option<ServerCommand>) -> Result<(), EmfManagerCliError> {
    server(command.unwrap_or(ServerCommand::List {
        display_type: DisplayType::Tabular,
    }))
    .await
}

async fn server(command: ServerCommand) -> Result<(), EmfManagerCliError> {
    match command {
        ServerCommand::List { display_type } => list_server(display_type).await?,
    };

    Ok(())
}
