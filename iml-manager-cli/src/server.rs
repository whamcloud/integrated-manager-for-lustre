// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::get,
    display_utils::{generate_table, start_spinner},
    error::ImlManagerCliError,
};
use iml_wire_types::{ApiList, EndpointName, Host};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers
    #[structopt(name = "list")]
    List,
}

pub async fn server_cli(command: ServerCommand) -> Result<(), ImlManagerCliError> {
    match command {
        ServerCommand::List => {
            let stop_spinner = start_spinner("Running command...");

            let hosts: ApiList<Host> =
                get(Host::endpoint_name(), serde_json::json!({"limit": 0})).await?;

            stop_spinner(None);

            tracing::debug!("Hosts: {:?}", hosts);

            let table = generate_table(
                &["Id", "FQDN", "State", "Nids"],
                hosts.objects.into_iter().map(|h| {
                    vec![
                        h.id.to_string(),
                        h.fqdn,
                        h.state,
                        h.nids.unwrap_or_else(|| vec![]).join(" "),
                    ]
                }),
            );

            table.printstd();
        }
    };

    Ok(())
}
