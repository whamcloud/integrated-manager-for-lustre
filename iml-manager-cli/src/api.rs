// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlManagerCliError;
use console::Term;
use structopt::{clap::arg_enum, StructOpt};

arg_enum! {
    #[derive(PartialEq, Debug)]
    pub enum ApiType {
        Delete,
        Get,
        Post,
        Put,
    }
}

#[derive(Debug, StructOpt)]
pub struct ApiCommand {
    #[structopt(possible_values = &ApiType::variants(), case_insensitive = true)]
    call: ApiType,

    path: String,

    /// Object to PUT or POST
    body: Option<String>,
}

pub async fn api_cli(command: ApiCommand) -> Result<(), ImlManagerCliError> {
    let term = Term::stdout();
    let client = iml_manager_client::get_client()?;
    let uri = iml_manager_client::create_api_url(command.path)?;
    let body: serde_json::Value = serde_json::from_str(&command.body.unwrap_or("{}".to_string()))?;

    if let Some(resp) = match command.call {
        ApiType::Delete => Some(client.delete(uri).send().await?),
        ApiType::Get => {
            let resp = client.get(uri).send().await?;
            let data: serde_json::Value = resp.json().await?;
            term.write_line(&format!("{}", data))?;
            None
        }
        ApiType::Post => Some(client.put(uri).json(&body).send().await?),
        ApiType::Put => Some(client.post(uri).json(&body).send().await?),
    } {
        term.write_line(&format!("{:?}", resp))?;
    }

    Ok(())
}
