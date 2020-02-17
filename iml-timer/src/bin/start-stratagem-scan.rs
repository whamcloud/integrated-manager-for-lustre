// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_manager_client::{get_client, post};
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

#[derive(serde::Serialize)]
struct StratagemData {
    filesystem: String,
    report_duration: Option<String>,
    purge_duration: Option<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let opts = App::from_args();

    let post_data = StratagemData {
        filesystem: opts.filesystem,
        report_duration: opts.report,
        purge_duration: opts.purge,
    };

    post(get_client()?, "run_stratagem", &post_data)
        .await?
        .error_for_status()?;

    tracing::info!("Sent request to run stratagem scan.");

    Ok(())
}
