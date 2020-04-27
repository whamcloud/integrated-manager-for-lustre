// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::get_all,
    display_utils::{wrap_fut, DisplayType, IntoDisplayType as _},
    error::ImlManagerCliError,
};
use console::Term;
use iml_wire_types::Volume;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum DevicesCommand {
    /// List all configured devices
    #[structopt(name = "list")]
    List {
        /// Set the display type
        ///
        /// The display type can be one of the following:
        /// tabular: display content in a table format
        /// json: return data in json format
        /// yaml: return data in yaml format
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
}

pub async fn devices_cli(command: DevicesCommand) -> Result<(), ImlManagerCliError> {
    match command {
        DevicesCommand::List { display_type } => {
            let fut_volumes = get_all::<Volume>();

            let volumes = wrap_fut("Fetching volumes...", fut_volumes).await?;

            tracing::debug!("Volumes: {:?}", volumes);

            let term = Term::stdout();

            let x = volumes.objects.into_display_type(display_type);

            term.write_line(&x).unwrap();
        }
    };

    Ok(())
}
