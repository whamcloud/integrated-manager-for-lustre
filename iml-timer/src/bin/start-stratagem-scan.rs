// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use reqwest;
use reqwest::{header, Client};
use serde::{Deserialize, Serialize};
use std::{env::var, io::Error, time::Duration};
use structopt::StructOpt;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[derive(Debug, StructOpt)]
#[structopt(name = "start-stratagem-scan")]
/// The start-stratagem-scan API
struct App {
    #[structopt(short = "f", long = "filesystem")]
    filesystem: String,

    #[structopt(short = "r", long = "report")]
    report: Option<String>,

    #[structopt(short = "p", long = "purge")]
    purge: Option<String>,
}

#[derive(Deserialize, Serialize)]
struct StratagemData {
    filesystem: String,
    report_duration: Option<String>,
    purge_duration: Option<String>,
}

/// Get a client that is able to make authenticated requests
/// against the API
pub fn get_client(api_user: &str, api_key: &str) -> Result<Client, Error> {
    let header_value = header::HeaderValue::from_str(&format!("ApiKey {}:{}", api_user, api_key))
        .map_err(|e| Error::new(std::io::ErrorKind::InvalidData, e.to_string()))?;

    let headers = vec![(header::AUTHORIZATION, header_value)]
        .into_iter()
        .collect();

    Client::builder()
        .timeout(Duration::from_secs(60))
        .default_headers(headers)
        .danger_accept_invalid_certs(true)
        .build()
        .map_err(|e| Error::new(std::io::ErrorKind::Other, e.to_string()))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let opts = App::from_args();

    let url = var("SERVER_HTTP_URL")?;
    let api_user = var("API_USER")?;
    let api_key = var("API_KEY")?;

    let post_data = StratagemData {
        filesystem: opts.filesystem,
        report_duration: opts.report,
        purge_duration: opts.purge,
    };

    get_client(&api_user, &api_key)?
        .post(&format!("{}/api/run_stratagem/", url))
        .header("AUTHORIZATION", format!("ApiKey {}:{}", api_user, api_key))
        .json(&post_data)
        .send()
        .await?
        .error_for_status()?;

    tracing::info!("Sent request to run stratagem scan.");
    Ok(())
}
