// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlManagerCliError;
use console::Term;
use structopt::{clap::arg_enum, StructOpt};
use tokio::io::{stdin, AsyncReadExt};

arg_enum! {
    #[derive(PartialEq, Debug)]
    pub enum ApiMethod {
        Delete,
        Get,
        Head,
        Patch,
        Post,
        Put,
    }
}

#[derive(Debug, StructOpt)]
pub struct ApiCommand {
    #[structopt(possible_values = &ApiMethod::variants(), case_insensitive = true)]
    method: ApiMethod,

    path: String,

    /// PATH should not be cooked to start with /api/
    #[structopt(short, long)]
    raw: bool,

    /// JSON formatted body to send or "-" to read from stdin
    #[structopt(required_ifs(&[("method", "patch"),("method", "post"),("method", "put")]))]
    body: Option<String>,
}

pub async fn api_cli(command: ApiCommand) -> Result<(), ImlManagerCliError> {
    let term = Term::stdout();
    let client = iml_manager_client::get_client()?;
    let uri = if command.raw {
        iml_manager_client::create_url(command.path)?
    } else {
        iml_manager_client::create_api_url(command.path)?
    };

    let req = match command.method {
        ApiMethod::Delete => client.delete(uri),
        ApiMethod::Get => client.get(uri),
        ApiMethod::Head => client.head(uri),
        ApiMethod::Patch => client.patch(uri),
        ApiMethod::Post => client.post(uri),
        ApiMethod::Put => client.put(uri),
    };

    let body: Option<serde_json::Value> = if command.body == Some("-".to_string()) {
        let mut buf: Vec<u8> = Vec::new();
        stdin().read_to_end(&mut buf).await?;
        let s = String::from_utf8_lossy(&buf);
        Some(serde_json::from_str(&s)?)
    } else {
        command.body.map(|s| serde_json::from_str(&s)).transpose()?
    };

    let req = if let Some(data) = body {
        req.json(&data)
    } else {
        req
    };

    let resp = req.send().await?;
    let resp_txt = format!("{:?}", resp);
    let body = resp.text().await?;

    match serde_json::from_str::<serde_json::Value>(&body) {
        Ok(json) => term.write_line(&format!("{}", json)),
        Err(_) => {
            term.write_line(&resp_txt)?;
            term.write_line(&body.to_string())?;

            Ok(())
        }
    }?;

    Ok(())
}
